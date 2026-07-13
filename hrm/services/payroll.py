from decimal import Decimal
from datetime import datetime
from django.db.models import Sum
from .base import ORMService
from ..models import AdvanceSalary, Payroll, PayrollEmployee, Employee, Attendance
from config.logger import hrm_logger

MONTHS_MAP = {
    'January': '01', 'February': '02', 'March': '03', 'April': '04',
    'May': '05', 'June': '06', 'July': '07', 'August': '08',
    'September': '09', 'October': '10', 'November': '11', 'December': '12',
}
MONTHS = list(MONTHS_MAP.keys())
CURRENT_YEAR = datetime.now().year
YEARS = [CURRENT_YEAR - 1, CURRENT_YEAR, CURRENT_YEAR + 1]


class PayrollService(ORMService):
    model = Payroll

    @classmethod
    def _resolve(cls, doc_id, model_class=None):
        if not doc_id:
            return None
        mc = model_class or cls.model
        try:
            return mc.objects.get(pk=doc_id)
        except (mc.DoesNotExist, ValueError):
            pass
        return mc.objects.filter(pk=doc_id).first()

    @classmethod
    def add_advance(cls, data, user):
        doc_id = data.get('doc_id')
        emp_name = data.get('employee', '')
        emp = Employee.objects.filter(name=emp_name).first()

        if doc_id:
            instance = cls._resolve(doc_id, AdvanceSalary)
            if instance:
                instance.employee = emp or instance.employee
                instance.amount = float(data.get('amount', 0))
                instance.deduct_month = data.get('deduct_month', instance.deduct_month)
                instance.reason = data.get('reason', '')
                instance.updated_by = user
                instance.save()
            return 'updated'
        else:
            AdvanceSalary.objects.create(
                employee=emp,
                amount=float(data.get('amount', 0)),
                deduct_month=data.get('deduct_month', ''),
                reason=data.get('reason', ''),
                status='Pending',
                created_by=user,
                updated_by=user,
            )
            return 'created'

    @classmethod
    def delete_advance(cls, doc_id):
        instance = cls._resolve(doc_id, AdvanceSalary)
        if instance:
            instance.is_active = False
            instance.save(update_fields=['is_active'])

    @classmethod
    def generate_salary(cls, data, user):
        month = data.get('month')
        year = data.get('year')
        period = f"{month} {year}"
        month_num = MONTHS_MAP.get(month, '01')
        target_period = f"{year}-{month_num}"

        active_employees = Employee.objects.filter(status='Active', is_active=True)
        employee_count = active_employees.count()

        total_net_pay = Decimal('0.00')
        payroll_entries = []

        for emp in active_employees:
            basic = Decimal(str(emp.basic_salary or 0))
            house_rent = Decimal(str(emp.house_rent or 0))
            medical = Decimal(str(emp.medical_allowance or 0))
            conveyance = Decimal(str(emp.conveyance_allowance or 0))
            util = Decimal(str(emp.utility or 0))
            mobile = Decimal(str(emp.mobile_bill or 0))
            gross = basic + house_rent + medical + conveyance + util + mobile

            absent_count = Attendance.objects.filter(
                employee=emp, date__startswith=target_period, status='Absent'
            ).count()

            daily_rate = basic / Decimal('30') if basic else Decimal('0')
            absent_deduction = (daily_rate * Decimal(str(absent_count))).quantize(Decimal('0.01'))

            advance_total = AdvanceSalary.objects.filter(
                employee=emp, deduct_month=target_period, is_active=True
            ).exclude(status='Deducted').aggregate(total=Sum('amount'))['total'] or Decimal('0')

            tax_deduction = (basic * Decimal('0.05')).quantize(Decimal('0.01'))

            total_deductions = absent_deduction + advance_total + tax_deduction
            net = (gross - total_deductions).quantize(Decimal('0.01'))
            if net < 0:
                net = Decimal('0.00')

            total_net_pay += net
            payroll_entries.append({
                'employee': emp,
                'basic_salary': basic,
                'house_rent': house_rent,
                'medical_allowance': medical,
                'conveyance_allowance': conveyance,
                'utility': util,
                'mobile_bill': mobile,
                'gross_pay': gross,
                'deductions': total_deductions,
                'net_pay': net,
            })

        total_net_pay = total_net_pay.quantize(Decimal('0.01'))

        doc_id = data.get('doc_id')
        if doc_id:
            payroll = cls._resolve(doc_id)
            if payroll:
                payroll.period = period
                payroll.employee_count = employee_count
                payroll.total_net_pay = float(total_net_pay)
                payroll.updated_by = user
                payroll.save()
                PayrollEmployee.objects.filter(payroll=payroll).delete()
        else:
            payroll = Payroll.objects.create(
                period=period,
                employee_count=employee_count,
                total_net_pay=float(total_net_pay),
                status='Generated',
                created_by=user,
                updated_by=user,
            )
        for entry in payroll_entries:
            PayrollEmployee.objects.create(payroll=payroll, **entry)

        for entry in payroll_entries:
            AdvanceSalary.objects.filter(
                employee=entry['employee'], deduct_month=target_period, status='Pending'
            ).update(status='Deducted')

        return 'updated' if doc_id else 'created'

    @classmethod
    def disburse_payroll(cls, doc_id, user):
        payroll = cls._resolve(doc_id)
        if not payroll or payroll.status == 'Disbursed':
            return None

        payroll.status = 'Disbursed'
        payroll.updated_by = user
        payroll.save(update_fields=['status', 'updated_by'])

        total_net_pay = float(payroll.total_net_pay or 0)
        period = payroll.period or ''

        try:
            from django.db import connections
            with connections['default'].cursor() as cursor:
                cursor.execute("SELECT id FROM fin_chart_of_accounts WHERE account_code = '51000' LIMIT 1")
                exp_row = cursor.fetchone()
                exp_id = str(exp_row[0]) if exp_row else '51000_fallback'

                cursor.execute("SELECT id FROM fin_chart_of_accounts WHERE account_code = '11100' LIMIT 1")
                cash_row = cursor.fetchone()
                cash_id = str(cash_row[0]) if cash_row else '11100_fallback'
        except Exception:
            exp_id = '51000_fallback'
            cash_id = '11100_fallback'

        lines = [
            {'account_id': exp_id, 'debit_amount': total_net_pay, 'credit_amount': 0.0},
            {'account_id': cash_id, 'debit_amount': 0.0, 'credit_amount': total_net_pay},
        ]

        try:
            from django.db import connections
            with connections['default'].cursor() as cursor:
                entry_code = f"AUTO-PAYROLL-{datetime.now().strftime('%Y%m%d')}"
                cursor.execute(
                    "INSERT INTO fin_journal_entries "
                    "(entry_code, posting_date, reference_document, narration, status, created_by, approved_by, lines, created_at, updated_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())",
                    [entry_code, datetime.now().strftime('%Y-%m-%d'),
                     f"Payroll {period}", f"Automated posting of net pay for period {period}",
                     'Posted', 'System', user.username if user else 'System', str(lines)]
                )
        except Exception as e:
            hrm_logger.error(f"Error posting journal entry: {e}")

        return 'disbursed'

    @classmethod
    def delete(cls, doc_id):
        instance = cls._resolve(doc_id)
        if instance:
            instance.is_active = False
            instance.save(update_fields=['is_active'])

    @classmethod
    def get_payroll_context(cls):
        advances = list(AdvanceSalary.objects.filter(is_active=True).select_related('employee').order_by('-created_at').values(
            'pk', 'employee__name', 'amount', 'deduct_month', 'reason', 'status',
        ))
        for a in advances:
            a['id'] = a.pop('pk') or ''
            a['employee'] = a.pop('employee__name', '')

        payrolls = list(Payroll.objects.filter(is_active=True).order_by('-created_at').values(
            'pk', 'period', 'employee_count', 'total_net_pay', 'status',
        ))
        for p in payrolls:
            p['id'] = p.pop('pk') or ''

        try:
            employees = [{'name': e.name} for e in Employee.objects.filter(is_active=True) if e.name]
        except Exception:
            employees = []

        return advances, payrolls, employees, MONTHS, YEARS
