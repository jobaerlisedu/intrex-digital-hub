from rest_framework import serializers
from .base import FirestoreModelSerializer
from .. import models


class DepartmentSerializer(FirestoreModelSerializer):
    class Meta:
        model = models.Department
        collection_name = 'org_departments'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class PositionSerializer(FirestoreModelSerializer):
    class Meta:
        model = models.Position
        collection_name = 'org_positions'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class EmployeeSerializer(FirestoreModelSerializer):
    name = serializers.ReadOnlyField()

    class Meta:
        model = models.Employee
        collection_name = 'hrm_employees'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class RecruitmentCandidateSerializer(FirestoreModelSerializer):
    class Meta:
        model = models.RecruitmentCandidate
        collection_name = 'hrm_recruitment_candidates'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class RecruitmentShortlistSerializer(FirestoreModelSerializer):
    class Meta:
        model = models.RecruitmentShortlist
        collection_name = 'hrm_recruitment_shortlists'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class RecruitmentInterviewSerializer(FirestoreModelSerializer):
    class Meta:
        model = models.RecruitmentInterview
        collection_name = 'hrm_recruitment_interviews'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class RecruitmentSelectionSerializer(FirestoreModelSerializer):
    class Meta:
        model = models.RecruitmentSelection
        collection_name = 'hrm_recruitment_selections'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class AttendanceSerializer(FirestoreModelSerializer):
    class Meta:
        model = models.Attendance
        collection_name = 'hrm_attendances'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class LeaveSerializer(FirestoreModelSerializer):
    class Meta:
        model = models.Leave
        collection_name = 'hrm_leaves'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class HolidaySerializer(FirestoreModelSerializer):
    class Meta:
        model = models.Holiday
        collection_name = 'hrm_holidays'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class AdvanceSalarySerializer(FirestoreModelSerializer):
    class Meta:
        model = models.AdvanceSalary
        collection_name = 'hrm_advances'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_amount(self, value):
        from config.firebase import db
        employee_ref = (self.instance.get('employee') if isinstance(self.instance, dict) else
                       getattr(self.instance, 'employee', None) if self.instance else None)
        if not employee_ref and self.initial_data.get('employee'):
            employee_ref = self.initial_data['employee']
        if employee_ref:
            try:
                employee_id = employee_ref.split('/')[-1] if '/' in str(employee_ref) else str(employee_ref)
                emp_doc = db.collection('hrm_employees').document(employee_id).get()
                if emp_doc.exists:
                    emp_data = emp_doc.to_dict() or {}
                    if emp_data.get('basic_salary'):
                        import decimal
                        max_allowed = decimal.Decimal(str(emp_data['basic_salary'])) * 2
            except Exception:
                pass
        return value

    def validate(self, data):
        from config.firebase import db as firestore_db
        employee_ref = (self.instance.get('employee') if isinstance(self.instance, dict) else
                       getattr(self.instance, 'employee', None) if self.instance else data.get('employee'))
        if employee_ref:
            try:
                existing = list(firestore_db.collection('hrm_advances')
                               .where('employee', '==', employee_ref)
                               .where('status', '==', 'Pending')
                               .where('is_active', '==', True)
                               .stream())
                instance_id = (self.instance.get('id') if isinstance(self.instance, dict)
                              else getattr(self.instance, 'id', None) if self.instance else None)
                if instance_id:
                    existing = [e for e in existing if e.id != instance_id]
                if existing:
                    raise serializers.ValidationError(
                        "This employee already has a pending advance request."
                    )
            except serializers.ValidationError:
                raise
            except Exception:
                pass
        return data


class PayrollSerializer(FirestoreModelSerializer):
    class Meta:
        model = models.Payroll
        collection_name = 'hrm_payrolls'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class PayrollEmployeeSerializer(FirestoreModelSerializer):
    class Meta:
        model = models.PayrollEmployee
        collection_name = 'hrm_payroll_employees'
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class EmployeeShiftSerializer(FirestoreModelSerializer):
    class Meta:
        model = models.EmployeeShift
        collection_name = 'hrm_employee_shifts'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class OnboardingTaskSerializer(FirestoreModelSerializer):
    class Meta:
        model = models.OnboardingTask
        collection_name = 'hrm_onboarding_tasks'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class ExitClearanceSerializer(FirestoreModelSerializer):
    class Meta:
        model = models.ExitClearance
        collection_name = 'hrm_exit_clearances'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class ExpenseClaimSerializer(FirestoreModelSerializer):
    class Meta:
        model = models.ExpenseClaim
        collection_name = 'hrm_expense_claims'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class DocumentSerializer(FirestoreModelSerializer):
    class Meta:
        model = models.Document
        collection_name = 'hrm_documents'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class AssetSerializer(FirestoreModelSerializer):
    class Meta:
        model = models.Asset
        collection_name = 'hrm_assets'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class HRMSettingSerializer(FirestoreModelSerializer):
    class Meta:
        model = models.HRMSetting
        collection_name = 'hrm_settings'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# ── Performance Management ─────────────────────────────────────────────

class ReviewCycleSerializer(FirestoreModelSerializer):
    class Meta:
        model = models.ReviewCycle
        collection_name = 'hrm_review_cycles'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class RatingTemplateSerializer(FirestoreModelSerializer):
    scales = serializers.SerializerMethodField()

    class Meta:
        model = models.RatingTemplate
        collection_name = 'hrm_rating_templates'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_scales(self, obj):
        from config.firebase import db as firestore_db
        template_ref = f'hrm_rating_templates/{obj.get("id")}'
        scale_docs = firestore_db.collection('hrm_rating_scales')\
            .where('template', '==', template_ref)\
            .where('is_active', '==', True)\
            .order_by('order')\
            .stream()
        scales = [{'id': d.id, **d.to_dict()} for d in scale_docs]
        return RatingScaleSerializer(scales, many=True).data


class RatingScaleSerializer(FirestoreModelSerializer):
    class Meta:
        model = models.RatingScale
        collection_name = 'hrm_rating_scales'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class KPISerializer(FirestoreModelSerializer):
    class Meta:
        model = models.KPI
        collection_name = 'hrm_kpis'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class EmployeeKPISerializer(FirestoreModelSerializer):
    employee_name = serializers.ReadOnlyField()
    kpi_name = serializers.ReadOnlyField()
    cycle_name = serializers.ReadOnlyField()

    class Meta:
        model = models.EmployeeKPI
        collection_name = 'hrm_employee_kpis'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class PerformanceReviewSerializer(FirestoreModelSerializer):
    employee_name = serializers.ReadOnlyField()
    reviewer_name = serializers.ReadOnlyField()
    cycle_name = serializers.ReadOnlyField()

    class Meta:
        model = models.PerformanceReview
        collection_name = 'hrm_performance_reviews'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class PIPMilestoneSerializer(FirestoreModelSerializer):
    class Meta:
        model = models.PIPMilestone
        collection_name = 'hrm_pip_milestones'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class PerformanceImprovementPlanSerializer(FirestoreModelSerializer):
    employee_name = serializers.ReadOnlyField()
    milestones = serializers.SerializerMethodField()

    def get_milestones(self, obj):
        milestones_data = obj.get('milestones', []) if isinstance(obj, dict) else []
        if milestones_data:
            if isinstance(milestones_data[0], dict):
                return PIPMilestoneSerializer(milestones_data, many=True).data
        return milestones_data

    class Meta:
        model = models.PerformanceImprovementPlan
        collection_name = 'hrm_pips'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# ── Leave Balance ──────────────────────────────────────────────────────

class LeavePolicySerializer(FirestoreModelSerializer):
    class Meta:
        model = models.LeavePolicy
        collection_name = 'hrm_leave_policies'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class LeaveBalanceSerializer(FirestoreModelSerializer):
    employee_name = serializers.ReadOnlyField()

    class Meta:
        model = models.LeaveBalance
        collection_name = 'hrm_leave_balances'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'available']


# ── Training & Development ─────────────────────────────────────────────

class TrainingNeedSerializer(FirestoreModelSerializer):
    employee_name = serializers.ReadOnlyField()

    class Meta:
        model = models.TrainingNeed
        collection_name = 'hrm_training_needs'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class DevelopmentPlanSerializer(FirestoreModelSerializer):
    employee_name = serializers.ReadOnlyField()

    class Meta:
        model = models.DevelopmentPlan
        collection_name = 'hrm_development_plans'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class TrainingNominationSerializer(FirestoreModelSerializer):
    employee_name = serializers.ReadOnlyField()

    class Meta:
        model = models.TrainingNomination
        collection_name = 'hrm_training_nominations'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# ── Notifications ─────────────────────────────────────────────────────

class NotificationSerializer(FirestoreModelSerializer):
    class Meta:
        model = models.Notification
        collection_name = 'hrm_notifications'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'read_at']


class NotificationPreferenceSerializer(FirestoreModelSerializer):
    class Meta:
        model = models.NotificationPreference
        collection_name = 'hrm_notification_preferences'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class DeviceTokenSerializer(FirestoreModelSerializer):
    class Meta:
        model = models.DeviceToken
        collection_name = 'hrm_device_tokens'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# ── Succession Planning ────────────────────────────────────────────────

class KeyPositionSerializer(FirestoreModelSerializer):
    position_title_display = serializers.ReadOnlyField()
    department_name = serializers.ReadOnlyField()
    incumbent_name = serializers.ReadOnlyField()

    class Meta:
        model = models.KeyPosition
        collection_name = 'hrm_key_positions'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class SuccessorCandidateSerializer(FirestoreModelSerializer):
    employee_name = serializers.ReadOnlyField()

    class Meta:
        model = models.SuccessorCandidate
        collection_name = 'hrm_successor_candidates'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class SuccessionPlanSerializer(FirestoreModelSerializer):
    department_name = serializers.ReadOnlyField()

    class Meta:
        model = models.SuccessionPlan
        collection_name = 'hrm_succession_plans'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# ── Employee Skills & Education ──────────────────────────────────────────

class EmployeeEducationSerializer(FirestoreModelSerializer):
    class Meta:
        model = models.EmployeeEducation
        collection_name = 'hrm_employee_education'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class EmployeeExperienceSerializer(FirestoreModelSerializer):
    class Meta:
        model = models.EmployeeExperience
        collection_name = 'hrm_employee_experience'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class EmployeeSkillSerializer(FirestoreModelSerializer):
    class Meta:
        model = models.EmployeeSkill
        collection_name = 'hrm_employee_skills'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class CompetencySerializer(FirestoreModelSerializer):
    class Meta:
        model = models.Competency
        collection_name = 'hrm_competencies'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class CompetencyRatingSerializer(FirestoreModelSerializer):
    class Meta:
        model = models.CompetencyRating
        collection_name = 'hrm_competency_ratings'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class CandidateDocumentSerializer(FirestoreModelSerializer):
    class Meta:
        model = models.CandidateDocument
        collection_name = 'hrm_candidate_documents'
        fields = '__all__'
        read_only_fields = ['id', 'uploaded_at']


# ── 360 Feedback ─────────────────────────────────────────────────────────

class FeedbackQuestionSerializer(FirestoreModelSerializer):
    class Meta:
        model = models.FeedbackQuestion
        collection_name = 'hrm_feedback_questions'
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class FeedbackRequestSerializer(FirestoreModelSerializer):
    class Meta:
        model = models.FeedbackRequest
        collection_name = 'hrm_feedback_requests'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class FeedbackResponseSerializer(FirestoreModelSerializer):
    class Meta:
        model = models.FeedbackResponse
        collection_name = 'hrm_feedback_responses'
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


# ── Engagement Surveys ───────────────────────────────────────────────────

class EngagementSurveySerializer(FirestoreModelSerializer):
    class Meta:
        model = models.EngagementSurvey
        collection_name = 'hrm_engagement_surveys'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class SurveyQuestionSerializer(FirestoreModelSerializer):
    class Meta:
        model = models.SurveyQuestion
        collection_name = 'hrm_survey_questions'
        fields = '__all__'
        read_only_fields = ['id']


class SurveyResponseSerializer(FirestoreModelSerializer):
    class Meta:
        model = models.SurveyResponse
        collection_name = 'hrm_survey_responses'
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


# ── Compliance Calendar ──────────────────────────────────────────────────

class ComplianceReminderSerializer(FirestoreModelSerializer):
    class Meta:
        model = models.ComplianceReminder
        collection_name = 'hrm_compliance_reminders'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# ── Talent Review & 9-Box ────────────────────────────────────────────────

class TalentReviewMeetingSerializer(FirestoreModelSerializer):
    class Meta:
        model = models.TalentReviewMeeting
        collection_name = 'hrm_talent_review_meetings'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class NineBoxCellSerializer(FirestoreModelSerializer):
    class Meta:
        model = models.NineBoxCell
        collection_name = 'hrm_nine_box_cells'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# ── Disciplinary Management ────────────────────────────────────────────

class DisciplinaryCaseSerializer(FirestoreModelSerializer):
    employee_name = serializers.ReadOnlyField()
    employee_emp_id = serializers.ReadOnlyField()

    class Meta:
        model = models.DisciplinaryCase
        collection_name = 'hrm_disciplinary_cases'
        fields = '__all__'
        read_only_fields = ['id', 'case_number', 'created_at', 'updated_at']


class DisciplinaryHearingSerializer(FirestoreModelSerializer):
    case_number = serializers.ReadOnlyField()

    class Meta:
        model = models.DisciplinaryHearing
        collection_name = 'hrm_disciplinary_hearings'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class DisciplinaryActionSerializer(FirestoreModelSerializer):
    case_number = serializers.ReadOnlyField()
    employee_name = serializers.ReadOnlyField()

    class Meta:
        model = models.DisciplinaryAction
        collection_name = 'hrm_disciplinary_actions'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class DisciplinaryAppealSerializer(FirestoreModelSerializer):
    action_type = serializers.ReadOnlyField()
    case_number = serializers.ReadOnlyField()

    class Meta:
        model = models.DisciplinaryAppeal
        collection_name = 'hrm_disciplinary_appeals'
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
