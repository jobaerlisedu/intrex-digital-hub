from config.firebase import db
from config.logger import hrm_logger
from ..audit import enrich_with_audit
from ..validators import validate_advance_data
from ..views_helpers import get_collection_data
from .base import FirestoreService


class PayrollService(FirestoreService):
    collection_name = 'hrm_payrolls'

    @classmethod
    def add_advance(cls, data, user):
        doc_id = data.get('doc_id')
        base_data = {
            'employee': data.get('employee'),
            'amount': float(data.get('amount', 0)),
            'deduct_month': data.get('deduct_month'),
            'reason': data.get('reason', ''),
            'status': 'Pending',
        }
        if doc_id:
            db.collection('hrm_advances').document(doc_id).update(
                enrich_with_audit(base_data, user, is_update=True)
            )
            return 'updated'
        else:
            db.collection('hrm_advances').add(
                enrich_with_audit(base_data, user, is_update=False)
            )
            return 'created'

    @classmethod
    def delete_advance(cls, doc_id):
        db.collection('hrm_advances').document(doc_id).delete()

    @classmethod
    def generate_salary(cls, data, user):
        month = data.get('month')
        year = data.get('year')
        period = f"{month} {year}"

        months_map = {
            'January': '01', 'February': '02', 'March': '03', 'April': '04',
            'May': '05', 'June': '06', 'July': '07', 'August': '08',
            'September': '09', 'October': '10', 'November': '11', 'December': '12'
        }
        month_num = months_map.get(month, '01')
        target_period = f"{year}-{month_num}"

        emp_docs = list(db.collection('hrm_employees').stream())
        active_employees = [e.to_dict() for e in emp_docs if e.to_dict().get('status') == 'Active']
        employee_count = len(active_employees)

        total_net_pay = 0.0
        for emp in active_employees:
            emp_name = emp.get('name')
            basic_salary = float(emp.get('basic_salary', 0))
            gross_salary = float(emp.get('gross_salary', 0))

            absent_count = 0
            att_docs = db.collection('hrm_attendance').where('name', '==', emp_name).stream()
            for doc in att_docs:
                d = doc.to_dict()
                if d.get('date', '').startswith(target_period) and d.get('status') == 'Absent':
                    absent_count += 1

            daily_rate = basic_salary / 30.0 if basic_salary > 0 else 0.0
            absent_deduction = round(daily_rate * absent_count, 2)

            advance_deduction = 0.0
            adv_docs = db.collection('hrm_advances').where('employee', '==', emp_name).where('deduct_month', '==', target_period).stream()
            for doc in adv_docs:
                advance_deduction += float(doc.to_dict().get('amount', 0))

            tax_deduction = round(basic_salary * 0.05, 2)
            net_pay = round(gross_salary - absent_deduction - advance_deduction - tax_deduction, 2)
            if net_pay < 0:
                net_pay = 0.0
            total_net_pay += net_pay

        total_net_pay = round(total_net_pay, 2)

        doc_id = data.get('doc_id')
        payload = {
            'period': period,
            'employee_count': employee_count,
            'total_net_pay': total_net_pay,
            'status': 'Generated',
        }

        if doc_id:
            cls.update(doc_id, payload, user)
            return 'updated'
        else:
            cls.create(payload, user)
            return 'created'

    @classmethod
    def disburse_payroll(cls, doc_id, user):
        from datetime import datetime
        pr_ref = db.collection('hrm_payrolls').document(doc_id)
        pr_data = pr_ref.get().to_dict()
        if not pr_data or pr_data.get('status') == 'Disbursed':
            return None

        pr_ref.update(enrich_with_audit({'status': 'Disbursed'}, user, is_update=True))

        total_net_pay = float(pr_data.get('total_net_pay', 0.0))
        period = pr_data.get('period', '')

        coa_exp = list(db.collection('fin_chart_of_accounts').where('account_code', '==', '51000').stream())
        coa_cash = list(db.collection('fin_chart_of_accounts').where('account_code', '==', '11100').stream())
        exp_id = coa_exp[0].id if coa_exp else '51000_fallback'
        cash_id = coa_cash[0].id if coa_cash else '11100_fallback'

        lines = [
            {'account_id': exp_id, 'debit_amount': total_net_pay, 'credit_amount': 0.0},
            {'account_id': cash_id, 'debit_amount': 0.0, 'credit_amount': total_net_pay},
        ]

        je_data = {
            'entry_code': f"AUTO-PAYROLL-{datetime.now().strftime('%Y%m%d')}",
            'posting_date': datetime.now().strftime('%Y-%m-%d'),
            'reference_document': f"Payroll {period}",
            'narration': f"Automated posting of net pay for period {period}",
            'status': 'Posted',
            'created_by': 'System',
            'approved_by': user.username if user else 'System',
            'lines': lines,
        }
        db.collection('fin_journal_entries').add(enrich_with_audit(je_data, user, is_update=False))
        return 'disbursed'

    @classmethod
    def get_payroll_context(cls):
        advances = get_collection_data('hrm_advances', [])
        payrolls = get_collection_data('hrm_payrolls', [])
        try:
            emp_docs = db.collection('hrm_employees').stream()
            employees = [{'name': d.to_dict().get('name', '')} for d in emp_docs if d.to_dict().get('name')]
        except Exception:
            employees = []
        months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        from datetime import datetime
        current_year = datetime.now().year
        years = [current_year - 1, current_year, current_year + 1]
        return advances, payrolls, employees, months, years
