from decimal import Decimal
from django.db import transaction, models as db_models
from django.utils import timezone
from ..models import Employee, Payroll, PayrollEmployee, Leave, AdvanceSalary, Attendance


def calculate_payroll(period, employee_ids, user, tax_rate=Decimal('0.05')):
    employees = Employee.objects.filter(id__in=employee_ids, status='Active')
    year_month = period
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
            tax_deduction = (emp.basic_salary * tax_rate).quantize(Decimal('0.01'))
            advance_total = AdvanceSalary.objects.filter(
                employee=emp, deduct_month=year_month, status='Pending', is_active=True,
            ).aggregate(total=db_models.Sum('amount'))['total'] or Decimal('0.00')
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
                payroll=payroll, employee=emp,
                basic_salary=emp.basic_salary, house_rent=emp.house_rent,
                medical_allowance=emp.medical_allowance, conveyance_allowance=emp.conveyance_allowance,
                utility=emp.utility, mobile_bill=emp.mobile_bill,
                gross_pay=gross, deductions=total_deductions, net_pay=net,
            )
            total_net += net
            AdvanceSalary.objects.filter(
                employee=emp, deduct_month=year_month, status='Pending', is_active=True,
            ).update(status='Deducted')
        payroll.total_net_pay = total_net.quantize(Decimal('0.01'))
        payroll.save()
    return payroll


def get_employee_leave_balance(employee, leave_type='Annual'):
    from ..models import LeavePolicy, LeaveBalance
    policy = LeavePolicy.objects.filter(
        employee_type=employee.employee_type, leave_type=leave_type, is_active=True,
    ).first()
    entitled = policy.entitled_days if policy else 20
    period = timezone.now().strftime('%Y')
    balance, _ = LeaveBalance.objects.get_or_create(
        employee=employee, leave_type=leave_type, period=period,
        defaults={'entitled': entitled, 'used': 0, 'pending': 0},
    )
    return max(0, float(balance.entitled - balance.used - balance.pending))


def sync_document_compliance_reminders():
    from ..models import Document, ComplianceReminder
    docs = Document.objects.filter(is_active=True, expiry_date__isnull=False).select_related('employee')
    for doc in docs:
        reminder = ComplianceReminder.auto_create_from_document(doc)
        if reminder and reminder.due_date < timezone.now().date() and reminder.status != 'Completed':
            reminder.status = 'Overdue'
            reminder.save(update_fields=['status'])
    return {'synced': docs.count()}


def check_compliance_overdue_reminders():
    from ..models import ComplianceReminder
    today = timezone.now().date()
    count = ComplianceReminder.objects.filter(
        due_date__lt=today, is_active=True,
    ).exclude(status='Completed').update(status='Overdue')
    return {'marked_overdue': count}


def send_compliance_notifications():
    from ..models import ComplianceReminder
    from config.services.notification_service import NotificationService
    today = timezone.now().date()
    overdue = ComplianceReminder.objects.filter(status='Overdue', is_active=True).select_related('employee')
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
