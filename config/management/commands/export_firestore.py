import json, os, sys
from datetime import datetime, date
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.conf import settings
from config.firebase import db

EXPORT_DIR = settings.BASE_DIR / '_firestore_export'

COLLECTIONS = [
    # HRM
    'hrm_employees', 'hrm_attendance', 'hrm_leaves', 'hrm_advances',
    'hrm_expense_claims', 'hrm_assets', 'hrm_exit_clearance',
    'hrm_disciplinary_cases', 'hrm_disciplinary_appeals',
    'hrm_key_positions', 'hrm_successor_candidates',
    'hrm_notification_preferences', 'hrm_survey_questions',
    'hrm_compliance_reminders', 'hrm_talent_review_meetings',
    'hrm_leave_policies', 'hrm_rating_scales', 'hrm_settings',
    'org_positions', 'hrm_counters', 'hrm_employee_education',
    'hrm_employee_experience', 'hrm_employee_skills',
    'hrm_competencies', 'hrm_competency_ratings',
    'hrm_feedback_questions', 'hrm_feedback_requests',
    'hrm_feedback_responses', 'hrm_surveys', 'hrm_survey_responses',
    'hrm_notifications', 'hrm_device_tokens',
    'hrm_candidate_documents', 'hrm_payroll_employees',
    'hrm_rating_templates', 'hrm_leave_balances',
    'hrm_employee_kpis', 'hrm_training_needs',
    'hrm_development_plans', 'hrm_training_nominations',
    'hrm_succession_plans', 'hrm_pip_milestones',
    'hrm_performance_improvement_plans', 'hrm_review_cycles',
    'hrm_kpis', 'hrm_nine_box_cells',
    # Finance
    'fin_chart_of_accounts', 'fin_journal_entries',
    'fin_invoices', 'fin_vendor_bills', 'fin_payments',
    'fin_tax_codes', 'fin_audit_trail',
    # Inventory
    'inv_products', 'inv_vendors', 'inv_requisitions',
    'inv_rfqs', 'inv_quotations', 'inv_purchase_orders',
    'inv_goods_receipts', 'inv_inventory_ledger', 'inv_deliveries',
    # Solutions
    'sol_projects', 'sol_project_phases', 'sol_tasks',
    'sol_project_requisitions', 'sol_software_licenses',
    'sol_project_stakeholders', 'sol_meetings',
    # Training
    'trn_courses', 'trn_batches', 'trn_registrations',
    'trn_payments', 'trn_inquiries', 'trn_institutes',
    'trn_ambassadors', 'trn_commissions', 'trn_expenses',
    'trn_assessments', 'trn_certificates', 'trn_job_placements',
    'trn_classes',
    # System
    'sys_users', 'sys_audit_logs', 'sys_contacts',
]


def serialize_value(val):
    if val is None:
        return None
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, Decimal):
        return str(val)
    if hasattr(val, 'isoformat'):
        return val.isoformat()
    try:
        json.dumps(val)
        return val
    except (TypeError, OverflowError):
        return str(val)


def serialize_doc(doc):
    data = doc.to_dict() or {}
    serialized = {'_doc_id': doc.id}
    for key, val in data.items():
        serialized[key] = serialize_value(val)
    return serialized


class Command(BaseCommand):
    help = 'Export all Firestore collections to JSON files for MySQL migration'

    def add_arguments(self, parser):
        parser.add_argument('--collections', nargs='+', help='Specific collections to export')
        parser.add_argument('--output-dir', default=str(EXPORT_DIR), help='Output directory')

    def handle(self, *args, **options):
        collections = options.get('collections') or COLLECTIONS
        output_dir = options.get('output_dir')
        os.makedirs(output_dir, exist_ok=True)

        total_docs = 0
        for coll_name in collections:
            self.stdout.write(f"Exporting {coll_name}...", ending=' ')
            try:
                docs = list(db.collection(coll_name).stream())
                records = [serialize_doc(d) for d in docs]
                filepath = os.path.join(output_dir, f'{coll_name}.json')
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(records, f, indent=2, ensure_ascii=False, default=str)
                count = len(records)
                total_docs += count
                self.stdout.write(self.style.SUCCESS(f"{count} docs"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"ERROR: {e}"))

        self.stdout.write(self.style.SUCCESS(
            f"\nExported {total_docs} total documents to {output_dir}/"
        ))
