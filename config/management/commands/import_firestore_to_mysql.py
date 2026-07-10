import json, os, sys
from datetime import datetime, date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from django.db import transaction

from registry.models import Person, Organization, PersonOrganization
from accounts.models import UserProfile, AuditLog, ActiveSession
from hrm.models import (
    Department, Position, Employee, RecruitmentCandidate,
    RecruitmentShortlist, RecruitmentInterview, RecruitmentSelection,
    CandidateDocument, Attendance, Leave, Holiday, AdvanceSalary,
    Payroll, PayrollEmployee, EmployeeShift, OnboardingTask,
    ExitClearance, ExpenseClaim, Document, Asset, HRMSetting,
    ReviewCycle, RatingTemplate, RatingScale, KPI, EmployeeKPI,
    PerformanceReview, PerformanceImprovementPlan, PIPMilestone,
    LeavePolicy, LeaveBalance, TrainingNeed, DevelopmentPlan,
    TrainingNomination, Notification, NotificationPreference,
    DeviceToken, KeyPosition, SuccessorCandidate, SuccessionPlan,
    EmployeeEducation, EmployeeExperience, EmployeeSkill,
    Competency, CompetencyRating, FeedbackQuestion, FeedbackRequest,
    FeedbackResponse, EngagementSurvey, SurveyQuestion, SurveyResponse,
    ComplianceReminder, TalentReviewMeeting, NineBoxCell,
    DisciplinaryCase, DisciplinaryHearing, DisciplinaryAction,
    DisciplinaryAppeal,
)
from billing.models import (
    ChartOfAccount, JournalEntry, JournalEntryLine, Invoice,
    InvoiceLine, VendorBill, VendorBillLine, Payment, TaxCode, AuditTrail,
)
from inventory.models import (
    Product, Vendor, Requisition, RequisitionItem, RFQ, RFQItem,
    Quotation, QuotationLineItem, PurchaseOrder, PurchaseOrderItem,
    GoodsReceipt, GoodsReceiptItem, InventoryLedger, Delivery,
)
from solutions.models import (
    Project, ProjectPhase, Task, ProjectRequisition,
    SoftwareLicense, ProjectStakeholder, Meeting,
)
from training.models import (
    Course, Batch, Registration, Payment as TrainingPayment,
    PaymentInstallment, Expense as TrainingExpense, Inquiry,
    Institute, Ambassador, Commission as TrainingCommission,
    Assessment, Certificate, JobPlacement, ClassSession,
)
from workflow.models import (
    WorkflowDefinition, WorkflowState, WorkflowTransition,
    WorkflowInstance, WorkflowLog,
)
from django.contrib.auth.models import User, Group

IMPORT_DIR = settings.BASE_DIR / '_firestore_export'

COLLECTION_MODEL_MAP = {
    # HRM
    'hrm_employees': Employee,
    'hrm_attendance': Attendance,
    'hrm_leaves': Leave,
    'hrm_advances': AdvanceSalary,
    'hrm_expense_claims': ExpenseClaim,
    'hrm_assets': Asset,
    'hrm_exit_clearance': ExitClearance,
    'hrm_disciplinary_cases': DisciplinaryCase,
    'hrm_disciplinary_appeals': DisciplinaryAppeal,
    'hrm_key_positions': KeyPosition,
    'hrm_successor_candidates': SuccessorCandidate,
    'hrm_notification_preferences': NotificationPreference,
    'hrm_survey_questions': SurveyQuestion,
    'hrm_compliance_reminders': ComplianceReminder,
    'hrm_talent_review_meetings': TalentReviewMeeting,
    'hrm_leave_policies': LeavePolicy,
    'hrm_rating_scales': RatingScale,
    'hrm_settings': HRMSetting,
    'org_positions': Position,
    'hrm_counters': None,
    'hrm_employee_education': EmployeeEducation,
    'hrm_employee_experience': EmployeeExperience,
    'hrm_employee_skills': EmployeeSkill,
    'hrm_competencies': Competency,
    'hrm_competency_ratings': CompetencyRating,
    'hrm_feedback_questions': FeedbackQuestion,
    'hrm_feedback_requests': FeedbackRequest,
    'hrm_feedback_responses': FeedbackResponse,
    'hrm_surveys': EngagementSurvey,
    'hrm_survey_responses': SurveyResponse,
    'hrm_notifications': Notification,
    'hrm_device_tokens': DeviceToken,
    'hrm_candidate_documents': CandidateDocument,
    'hrm_payroll_employees': PayrollEmployee,
    'hrm_rating_templates': RatingTemplate,
    'hrm_leave_balances': LeaveBalance,
    'hrm_employee_kpis': EmployeeKPI,
    'hrm_training_needs': TrainingNeed,
    'hrm_development_plans': DevelopmentPlan,
    'hrm_training_nominations': TrainingNomination,
    'hrm_succession_plans': SuccessionPlan,
    'hrm_pip_milestones': PIPMilestone,
    'hrm_performance_improvement_plans': PerformanceImprovementPlan,
    'hrm_review_cycles': ReviewCycle,
    'hrm_kpis': KPI,
    'hrm_nine_box_cells': NineBoxCell,
    # Finance
    'fin_chart_of_accounts': ChartOfAccount,
    'fin_journal_entries': JournalEntry,
    'fin_invoices': Invoice,
    'fin_vendor_bills': VendorBill,
    'fin_payments': Payment,
    'fin_tax_codes': TaxCode,
    'fin_audit_trail': AuditTrail,
    # Inventory
    'inv_products': Product,
    'inv_vendors': Vendor,
    'inv_requisitions': Requisition,
    'inv_rfqs': RFQ,
    'inv_quotations': Quotation,
    'inv_purchase_orders': PurchaseOrder,
    'inv_goods_receipts': GoodsReceipt,
    'inv_inventory_ledger': InventoryLedger,
    'inv_deliveries': Delivery,
    # Solutions
    'sol_projects': Project,
    'sol_project_phases': ProjectPhase,
    'sol_tasks': Task,
    'sol_project_requisitions': ProjectRequisition,
    'sol_software_licenses': SoftwareLicense,
    'sol_project_stakeholders': ProjectStakeholder,
    'sol_meetings': Meeting,
    # Training
    'trn_courses': Course,
    'trn_batches': Batch,
    'trn_registrations': Registration,
    'trn_payments': TrainingPayment,
    'trn_inquiries': Inquiry,
    'trn_institutes': Institute,
    'trn_ambassadors': Ambassador,
    'trn_commissions': TrainingCommission,
    'trn_expenses': TrainingExpense,
    'trn_assessments': Assessment,
    'trn_certificates': Certificate,
    'trn_job_placements': JobPlacement,
    'trn_classes': ClassSession,
    # System (handled separately)
    'sys_users': None,
    'sys_audit_logs': None,
    'sys_contacts': None,
}

FIELD_MAP_OVERRIDES = {
    Employee: {
        'department': ('department_id', lambda v: Department.objects.filter(firestore_id=v).first().pk if v else None),
        'position': ('position_id', lambda v: Position.objects.filter(firestore_id=v).first().pk if v else None),
        'sub_department': ('sub_department_id', lambda v: Department.objects.filter(firestore_id=v).first().pk if v else None),
        'reporting_to': ('reporting_to_id', lambda v: Employee.objects.filter(firestore_id=v).first().pk if v else None),
    },
    Attendance: {
        'employee': ('employee_id', lambda v: Employee.objects.filter(firestore_id=v).first().pk if v else None),
    },
    Leave: {
        'employee': ('employee_id', lambda v: Employee.objects.filter(firestore_id=v).first().pk if v else None),
    },
}

SKIP_FIELDS = {'_doc_id', 'createdAt', 'updatedAt', 'id'}

MODEL_FIELD_TYPES = {}
for model_cls in COLLECTION_MODEL_MAP.values():
    if model_cls is None:
        continue
    type_map = {}
    for f in model_cls._meta.get_fields():
        if hasattr(f, 'get_internal_type'):
            type_map[f.name] = f.get_internal_type()
    MODEL_FIELD_TYPES[model_cls] = type_map


def parse_value(val, target_type):
    if val is None:
        return None
    if target_type == 'DecimalField' and isinstance(val, str):
        return Decimal(val)
    if target_type in ('DateField', 'DateTimeField') and isinstance(val, str):
        try:
            return datetime.fromisoformat(val.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return None
    return val


def import_collection(coll_name, records, stdout, style):
    model_cls = COLLECTION_MODEL_MAP.get(coll_name)
    if model_cls is None:
        stdout.write(f"  Skipping {coll_name} (no model mapping)")
        return 0

    overrides = FIELD_MAP_OVERRIDES.get(model_cls, {})
    field_types = MODEL_FIELD_TYPES.get(model_cls, {})
    created = 0
    errors = 0

    for record in records:
        doc_id = record.get('_doc_id', '')
        try:
            kwargs = {'firestore_id': doc_id}
            for key, val in record.items():
                if key in SKIP_FIELDS:
                    continue
                if key in overrides:
                    target_field, resolver = overrides[key]
                    kwargs[target_field] = resolver(val)
                    continue
                internal_type = field_types.get(key)
                if internal_type is None or internal_type == 'ForeignKey':
                    continue
                kwargs[key] = parse_value(val, internal_type)

            model_cls.objects.update_or_create(
                firestore_id=doc_id,
                defaults=kwargs
            )
            created += 1
        except Exception as e:
            stdout.write(style.ERROR(f"    Error importing {doc_id}: {e}"))
            errors += 1

    return created


class Command(BaseCommand):
    help = 'Import Firestore JSON exports into MySQL via Django ORM'

    def add_arguments(self, parser):
        parser.add_argument('--collections', nargs='+', help='Specific collections to import')
        parser.add_argument('--input-dir', default=str(IMPORT_DIR), help='Input directory')

    def handle(self, *args, **options):
        input_dir = options.get('input_dir')
        if not os.path.isdir(input_dir):
            self.stderr.write(self.style.ERROR(f"Directory not found: {input_dir}"))
            self.stderr.write(self.style.ERROR("Run export_firestore first"))
            return

        files = sorted(os.listdir(input_dir))
        json_files = [f for f in files if f.endswith('.json')]

        if options.get('collections'):
            json_files = [f'{c}.json' for c in options['collections'] if os.path.exists(os.path.join(input_dir, f'{c}.json'))]

        total_created = 0
        for filename in json_files:
            coll_name = filename.replace('.json', '')
            filepath = os.path.join(input_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                records = json.load(f)
            count = len(records)
            if count == 0:
                self.stdout.write(f"{coll_name}: 0 records, skipping")
                continue

            self.stdout.write(f"Importing {coll_name} ({count} records)...")
            created = import_collection(coll_name, records, self.stdout, self.style)
            total_created += created
            self.stdout.write(self.style.SUCCESS(f"  {created} imported"))

        self.stdout.write(self.style.SUCCESS(f"\nTotal: {total_created} records imported"))
