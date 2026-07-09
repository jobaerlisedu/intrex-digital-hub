from decimal import Decimal
from django.db import transaction, models as db_models
from django.utils import timezone
from .models import Employee, Payroll, PayrollEmployee, Leave, AdvanceSalary, Attendance


def calculate_payroll(period, employee_ids, user, tax_rate=Decimal('0.05')):
    """
    Calculate payroll with deductions: tax, advances, absent days.
    - tax_rate: flat % deducted from basic salary (default 5%%)
    """
    employees = Employee.objects.filter(id__in=employee_ids, status='Active')
    year_month = period  # expected format YYYY-MM
    with transaction.atomic():
        payroll = Payroll.objects.create(
            period=period,
            employee_count=employees.count(),
            status='Draft',
            created_by=user,
        )
        total_net = Decimal('0.00')
        for emp in employees:
            gross = (emp.basic_salary + emp.house_rent + emp.medical_allowance +
                     emp.conveyance_allowance + emp.utility + emp.mobile_bill)

            # — Tax deduction (flat % of basic) —
            tax_deduction = (emp.basic_salary * tax_rate).quantize(Decimal('0.01'))

            # — Advance salary deductions for this period —
            advance_total = AdvanceSalary.objects.filter(
                employee=emp, deduct_month=year_month, status='Pending', is_active=True,
            ).aggregate(total=db_models.Sum('amount'))['total'] or Decimal('0.00')

            # — Absent day deduction (basic / 30 per day) —
            absent_count = Attendance.objects.filter(
                employee=emp, status='Absent', date__startswith=year_month,
            ).count()
            daily_rate = emp.basic_salary / Decimal('30') if emp.basic_salary else Decimal('0')
            absent_deduction = (daily_rate * Decimal(str(absent_count))).quantize(Decimal('0.01'))

            total_deductions = tax_deduction + advance_total + absent_deduction
            net = (gross - total_deductions).quantize(Decimal('0.01'))
            if net < 0:
                net = Decimal('0.00')

            PayrollEmployee.objects.create(
                payroll=payroll,
                employee=emp,
                basic_salary=emp.basic_salary,
                house_rent=emp.house_rent,
                medical_allowance=emp.medical_allowance,
                conveyance_allowance=emp.conveyance_allowance,
                utility=emp.utility,
                mobile_bill=emp.mobile_bill,
                gross_pay=gross,
                deductions=total_deductions,
                net_pay=net,
            )
            total_net += net

            # Mark advances as deducted
            AdvanceSalary.objects.filter(
                employee=emp, deduct_month=year_month, status='Pending', is_active=True,
            ).update(status='Deducted')

        payroll.total_net_pay = total_net.quantize(Decimal('0.01'))
        payroll.save()
    return payroll


def get_employee_leave_balance(employee, leave_type='Annual'):
    from .models import LeavePolicy, LeaveBalance
    from django.utils import timezone

    policy = LeavePolicy.objects.filter(
        employee_type=employee.employee_type,
        leave_type=leave_type,
        is_active=True,
    ).first()
    entitled = policy.entitled_days if policy else 20

    period = timezone.now().strftime('%Y')
    balance, _ = LeaveBalance.objects.get_or_create(
        employee=employee,
        leave_type=leave_type,
        period=period,
        defaults={'entitled': entitled, 'used': 0, 'pending': 0},
    )
    return max(0, float(balance.entitled - balance.used - balance.pending))


# ── Compliance Calendar Service ────────────────────────────────────

def sync_document_compliance_reminders():
    """Auto-create/update compliance reminders from Document expiry_dates."""
    from .models import Document, ComplianceReminder
    from django.utils import timezone

    docs = Document.objects.filter(
        is_active=True, expiry_date__isnull=False,
    ).select_related('employee')
    created_count = 0
    updated_count = 0

    for doc in docs:
        reminder = ComplianceReminder.auto_create_from_document(doc)
        if reminder:
            # Check if overdue
            if reminder.due_date < timezone.now().date() and reminder.status != 'Completed':
                reminder.status = 'Overdue'
                reminder.save(update_fields=['status'])

    return {'synced': docs.count()}


def check_compliance_overdue_reminders():
    """Mark reminders as overdue if past due_date and not completed."""
    from .models import ComplianceReminder
    from django.utils import timezone

    today = timezone.now().date()
    count = ComplianceReminder.objects.filter(
        due_date__lt=today, is_active=True,
    ).exclude(status='Completed').update(status='Overdue')
    return {'marked_overdue': count}


def send_compliance_notifications():
    """Send notifications for overdue and upcoming compliance reminders."""
    from .models import ComplianceReminder
    from config.services.notification_service import NotificationService
    from django.utils import timezone

    today = timezone.now().date()
    overdue = ComplianceReminder.objects.filter(
        status='Overdue', is_active=True,
    ).select_related('employee')
    upcoming = ComplianceReminder.objects.filter(
        due_date__gte=today, due_date__lte=today + timezone.timedelta(days=7),
        status='Pending', is_active=True,
    ).select_related('employee')

    sent = 0
    for reminder in overdue:
        if reminder.employee and reminder.employee.email:
            NotificationService.send_notification(
                recipient=reminder.employee.email,
                title='Compliance Reminder Overdue',
                message=f"'{reminder.title}' was due on {reminder.due_date}. Please complete immediately.",
                channel='email',
            )
            sent += 1

    for reminder in upcoming:
        if reminder.employee and reminder.employee.email:
            NotificationService.send_notification(
                recipient=reminder.employee.email,
                title='Upcoming Compliance Deadline',
                message=f"'{reminder.title}' is due on {reminder.due_date}.",
                channel='email',
            )
            sent += 1

    return {'notifications_sent': sent}
