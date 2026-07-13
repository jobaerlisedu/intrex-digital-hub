from decimal import Decimal
from datetime import datetime, timedelta, date
from django.db import models
from config.logger import hrm_logger
from ..models import (
    Employee, Attendance, AdvanceSalary, Payroll, PayrollEmployee,
    LeavePolicy, LeaveBalance, Document, ComplianceReminder,
)


def calculate_payroll(period, employee_ids, user, tax_rate=Decimal('0.05')):
    year_month = period
    employees = Employee.objects.filter(is_active=True, status='Active')
    filtered = []
    for emp in employees:
        if str(emp.pk) in employee_ids or emp.emp_id in employee_ids:
            filtered.append(emp)

    payroll = Payroll.objects.create(
        period=period,
        employee_count=len(filtered),
        status='Draft',
        created_by=user,
        updated_by=user,
    )
    total_net = Decimal('0.00')

    for emp in filtered:
        basic = Decimal(str(emp.basic_salary or '0'))
        house_rent = Decimal(str(emp.house_rent or '0'))
        medical = Decimal(str(emp.medical_allowance or '0'))
        conveyance = Decimal(str(emp.conveyance_allowance or '0'))
        utility = Decimal(str(emp.utility or '0'))
        mobile = Decimal(str(emp.mobile_bill or '0'))
        gross = basic + house_rent + medical + conveyance + utility + mobile

        tax_deduction = (basic * tax_rate).quantize(Decimal('0.01'))

        advance_total = AdvanceSalary.objects.filter(
            employee=emp, deduct_month=year_month, status='Pending', is_active=True
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')

        absent_count = Attendance.objects.filter(
            employee=emp, date__startswith=year_month, status='Absent'
        ).count()

        daily_rate = basic / Decimal('30') if basic else Decimal('0')
        absent_deduction = (daily_rate * Decimal(str(absent_count))).quantize(Decimal('0.01'))
        total_deductions = tax_deduction + advance_total + absent_deduction
        net = (gross - total_deductions).quantize(Decimal('0.01'))
        if net < 0:
            net = Decimal('0.00')

        PayrollEmployee.objects.create(
            payroll=payroll,
            employee=emp,
            basic_salary=basic,
            house_rent=house_rent,
            medical_allowance=medical,
            conveyance_allowance=conveyance,
            utility=utility,
            mobile_bill=mobile,
            gross_pay=gross,
            deductions=total_deductions,
            net_pay=net,
        )
        total_net += net

        AdvanceSalary.objects.filter(
            employee=emp, deduct_month=year_month, status='Pending'
        ).update(status='Deducted')

    payroll.total_net_pay = float(total_net.quantize(Decimal('0.01')))
    payroll.status = 'Generated'
    payroll.save(update_fields=['total_net_pay', 'status'])
    return str(payroll.pk)


def get_employee_leave_balance(employee_ref, leave_type='Annual'):
    if '/' in str(employee_ref):
        emp_id = employee_ref.split('/')[-1]
    else:
        emp_id = str(employee_ref)

    emp = Employee.objects.filter(pk=emp_id).first()
    if not emp:
        try:
            emp = Employee.objects.get(pk=emp_id)
        except (Employee.DoesNotExist, ValueError):
            return 0.0

    employee_type = emp.employee_type or ''
    period = str(date.today().year)

    policy = LeavePolicy.objects.filter(
        employee_type=employee_type, leave_type=leave_type, is_active=True
    ).first()
    entitled = int(policy.entitled_days) if policy else 20

    balance = LeaveBalance.objects.filter(
        employee=emp, leave_type=leave_type, period=period
    ).first()

    if balance:
        used = float(balance.used)
        pending = float(balance.pending)
    else:
        LeaveBalance.objects.create(
            employee=emp,
            leave_type=leave_type,
            period=period,
            entitled=entitled,
            used=0,
            pending=0,
        )
        used = 0
        pending = 0

    return max(0.0, float(entitled - used - pending))


def sync_document_compliance_reminders():
    synced = 0
    try:
        docs = Document.objects.filter(is_active=True)
        today = date.today()
        for d in docs:
            if not d.expiry_date:
                continue
            expiry_date = d.expiry_date
            due_date = expiry_date - timedelta(days=30)
            ComplianceReminder.objects.create(
                employee=d.employee,
                title=f"Document expiry: {d.document_type}",
                reminder_type='Document Expiry',
                due_date=due_date,
                status='Overdue' if due_date < today else 'Pending',
            )
            synced += 1
    except Exception as e:
        hrm_logger.error(f"Error syncing compliance reminders: {e}")
    return {'synced': synced}


def check_compliance_overdue_reminders():
    try:
        today = date.today()
        reminders = ComplianceReminder.objects.filter(is_active=True).exclude(status='Completed')
        count = 0
        for r in reminders:
            if r.due_date and r.due_date < today:
                r.status = 'Overdue'
                r.save(update_fields=['status'])
                count += 1
        return {'marked_overdue': count}
    except Exception as e:
        hrm_logger.error(f"Error checking overdue reminders: {e}")
        return {'marked_overdue': 0}


def send_compliance_notifications():
    from config.services.notification_service import NotificationService
    try:
        today = date.today()
        reminders = ComplianceReminder.objects.filter(is_active=True)
        sent = 0
        for r in reminders:
            if not r.due_date:
                continue
            emp = r.employee
            email = emp.email if emp else ''
            if not email:
                continue
            if r.status == 'Overdue':
                NotificationService.send_notification(
                    recipient=email,
                    title='Compliance Reminder Overdue',
                    message=f"'{r.title}' was due on {r.due_date}. Please complete immediately.",
                    channel='email',
                )
                sent += 1
            elif r.status == 'Pending' and today <= r.due_date <= today + timedelta(days=7):
                NotificationService.send_notification(
                    recipient=email,
                    title='Upcoming Compliance Deadline',
                    message=f"'{r.title}' is due on {r.due_date}.",
                    channel='email',
                )
                sent += 1
        return {'notifications_sent': sent}
    except Exception as e:
        hrm_logger.error(f"Error sending compliance notifications: {e}")
        return {'notifications_sent': 0}
