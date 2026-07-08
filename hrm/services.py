from django.db import transaction
from .models import Employee, Payroll, PayrollEmployee, Leave


def calculate_payroll(period, employee_ids, user):
    employees = Employee.objects.filter(id__in=employee_ids, status='Active')
    with transaction.atomic():
        payroll = Payroll.objects.create(
            period=period,
            employee_count=employees.count(),
            status='Draft',
            created_by=user,
        )
        total_net = 0
        for emp in employees:
            gross = (emp.basic_salary + emp.house_rent + emp.medical_allowance +
                     emp.conveyance_allowance + emp.utility + emp.mobile_bill)
            net = gross
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
                net_pay=net,
            )
            total_net += net
        payroll.total_net_pay = total_net
        payroll.save()
    return payroll


def get_employee_leave_balance(employee):
    taken = Leave.objects.filter(employee=employee, status='Approved').count()
    entitled = 20
    return max(0, entitled - taken)
