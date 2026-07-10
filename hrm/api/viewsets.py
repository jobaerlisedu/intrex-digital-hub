from rest_framework import viewsets, permissions
from .base import FirestoreViewSet
from .. import models
from .serializers import (
    DepartmentSerializer,
    PositionSerializer,
    EmployeeSerializer,
    RecruitmentCandidateSerializer,
    RecruitmentShortlistSerializer,
    RecruitmentInterviewSerializer,
    RecruitmentSelectionSerializer,
    AttendanceSerializer,
    LeaveSerializer,
    HolidaySerializer,
    AdvanceSalarySerializer,
    PayrollSerializer,
    PayrollEmployeeSerializer,
    EmployeeShiftSerializer,
    OnboardingTaskSerializer,
    ExitClearanceSerializer,
    ExpenseClaimSerializer,
    DocumentSerializer,
    AssetSerializer,
    HRMSettingSerializer,
    ReviewCycleSerializer,
    RatingTemplateSerializer,
    RatingScaleSerializer,
    KPISerializer,
    EmployeeKPISerializer,
    PerformanceReviewSerializer,
    PerformanceImprovementPlanSerializer,
    PIPMilestoneSerializer,
    LeavePolicySerializer,
    LeaveBalanceSerializer,
    TrainingNeedSerializer,
    DevelopmentPlanSerializer,
    TrainingNominationSerializer,
    NotificationSerializer,
    NotificationPreferenceSerializer,
    DeviceTokenSerializer,
    KeyPositionSerializer,
    SuccessorCandidateSerializer,
    SuccessionPlanSerializer,
    EmployeeEducationSerializer,
    EmployeeExperienceSerializer,
    EmployeeSkillSerializer,
    CompetencySerializer,
    CompetencyRatingSerializer,
    CandidateDocumentSerializer,
    FeedbackQuestionSerializer,
    FeedbackRequestSerializer,
    FeedbackResponseSerializer,
    EngagementSurveySerializer,
    SurveyQuestionSerializer,
    SurveyResponseSerializer,
    ComplianceReminderSerializer,
    TalentReviewMeetingSerializer,
    NineBoxCellSerializer,
    DisciplinaryCaseSerializer,
    DisciplinaryHearingSerializer,
    DisciplinaryActionSerializer,
    DisciplinaryAppealSerializer,
)


class DepartmentViewSet(FirestoreViewSet):
    collection_name = 'org_departments'
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated]


class PositionViewSet(FirestoreViewSet):
    collection_name = 'org_positions'
    serializer_class = PositionSerializer
    permission_classes = [permissions.IsAuthenticated]


class EmployeeViewSet(FirestoreViewSet):
    collection_name = 'hrm_employees'
    serializer_class = EmployeeSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = [
        'emp_id', 'department', 'position', 'employee_type',
        'status', 'gender', 'is_active',
    ]
    ordering_fields = [
        'emp_id', 'first_name', 'last_name', 'joining_date',
        'status', 'created_at', 'updated_at',
    ]


class RecruitmentCandidateViewSet(FirestoreViewSet):
    collection_name = 'hrm_recruitment_candidates'
    serializer_class = RecruitmentCandidateSerializer
    permission_classes = [permissions.IsAuthenticated]


class RecruitmentShortlistViewSet(FirestoreViewSet):
    collection_name = 'hrm_recruitment_shortlists'
    serializer_class = RecruitmentShortlistSerializer
    permission_classes = [permissions.IsAuthenticated]


class RecruitmentInterviewViewSet(FirestoreViewSet):
    collection_name = 'hrm_recruitment_interviews'
    serializer_class = RecruitmentInterviewSerializer
    permission_classes = [permissions.IsAuthenticated]


class RecruitmentSelectionViewSet(FirestoreViewSet):
    collection_name = 'hrm_recruitment_selections'
    serializer_class = RecruitmentSelectionSerializer
    permission_classes = [permissions.IsAuthenticated]


class AttendanceViewSet(FirestoreViewSet):
    collection_name = 'hrm_attendances'
    serializer_class = AttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]


class LeaveViewSet(FirestoreViewSet):
    collection_name = 'hrm_leaves'
    serializer_class = LeaveSerializer
    permission_classes = [permissions.IsAuthenticated]


class HolidayViewSet(FirestoreViewSet):
    collection_name = 'hrm_holidays'
    serializer_class = HolidaySerializer
    permission_classes = [permissions.IsAuthenticated]


class AdvanceSalaryViewSet(FirestoreViewSet):
    collection_name = 'hrm_advances'
    serializer_class = AdvanceSalarySerializer
    permission_classes = [permissions.IsAuthenticated]


class PayrollViewSet(FirestoreViewSet):
    collection_name = 'hrm_payrolls'
    serializer_class = PayrollSerializer
    permission_classes = [permissions.IsAuthenticated]


class PayrollEmployeeViewSet(FirestoreViewSet):
    collection_name = 'hrm_payroll_employees'
    serializer_class = PayrollEmployeeSerializer
    permission_classes = [permissions.IsAuthenticated]


class EmployeeShiftViewSet(FirestoreViewSet):
    collection_name = 'hrm_employee_shifts'
    serializer_class = EmployeeShiftSerializer
    permission_classes = [permissions.IsAuthenticated]


class OnboardingTaskViewSet(FirestoreViewSet):
    collection_name = 'hrm_onboarding_tasks'
    serializer_class = OnboardingTaskSerializer
    permission_classes = [permissions.IsAuthenticated]


class ExitClearanceViewSet(FirestoreViewSet):
    collection_name = 'hrm_exit_clearances'
    serializer_class = ExitClearanceSerializer
    permission_classes = [permissions.IsAuthenticated]


class ExpenseClaimViewSet(FirestoreViewSet):
    collection_name = 'hrm_expense_claims'
    serializer_class = ExpenseClaimSerializer
    permission_classes = [permissions.IsAuthenticated]


class DocumentViewSet(FirestoreViewSet):
    collection_name = 'hrm_documents'
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]


class AssetViewSet(FirestoreViewSet):
    collection_name = 'hrm_assets'
    serializer_class = AssetSerializer
    permission_classes = [permissions.IsAuthenticated]


class HRMSettingViewSet(FirestoreViewSet):
    collection_name = 'hrm_settings'
    serializer_class = HRMSettingSerializer
    permission_classes = [permissions.IsAuthenticated]


# ── Performance Management ─────────────────────────────────────────────

class ReviewCycleViewSet(FirestoreViewSet):
    collection_name = 'hrm_review_cycles'
    serializer_class = ReviewCycleSerializer
    permission_classes = [permissions.IsAuthenticated]


class RatingTemplateViewSet(FirestoreViewSet):
    collection_name = 'hrm_rating_templates'
    serializer_class = RatingTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]


class RatingScaleViewSet(FirestoreViewSet):
    collection_name = 'hrm_rating_scales'
    serializer_class = RatingScaleSerializer
    permission_classes = [permissions.IsAuthenticated]


class KPIViewSet(FirestoreViewSet):
    collection_name = 'hrm_kpis'
    serializer_class = KPISerializer
    permission_classes = [permissions.IsAuthenticated]


class EmployeeKPIViewSet(FirestoreViewSet):
    collection_name = 'hrm_employee_kpis'
    serializer_class = EmployeeKPISerializer
    permission_classes = [permissions.IsAuthenticated]


class PerformanceReviewViewSet(FirestoreViewSet):
    collection_name = 'hrm_performance_reviews'
    serializer_class = PerformanceReviewSerializer
    permission_classes = [permissions.IsAuthenticated]


class PerformanceImprovementPlanViewSet(FirestoreViewSet):
    collection_name = 'hrm_pips'
    serializer_class = PerformanceImprovementPlanSerializer
    permission_classes = [permissions.IsAuthenticated]


class PIPMilestoneViewSet(FirestoreViewSet):
    collection_name = 'hrm_pip_milestones'
    serializer_class = PIPMilestoneSerializer
    permission_classes = [permissions.IsAuthenticated]


# ── Leave Balance ──────────────────────────────────────────────────────

class LeavePolicyViewSet(FirestoreViewSet):
    collection_name = 'hrm_leave_policies'
    serializer_class = LeavePolicySerializer
    permission_classes = [permissions.IsAuthenticated]


class LeaveBalanceViewSet(FirestoreViewSet):
    collection_name = 'hrm_leave_balances'
    serializer_class = LeaveBalanceSerializer
    permission_classes = [permissions.IsAuthenticated]


# ── Training & Development ─────────────────────────────────────────────

class TrainingNeedViewSet(FirestoreViewSet):
    collection_name = 'hrm_training_needs'
    serializer_class = TrainingNeedSerializer
    permission_classes = [permissions.IsAuthenticated]


class DevelopmentPlanViewSet(FirestoreViewSet):
    collection_name = 'hrm_development_plans'
    serializer_class = DevelopmentPlanSerializer
    permission_classes = [permissions.IsAuthenticated]


class TrainingNominationViewSet(FirestoreViewSet):
    collection_name = 'hrm_training_nominations'
    serializer_class = TrainingNominationSerializer
    permission_classes = [permissions.IsAuthenticated]


# ── Notifications ─────────────────────────────────────────────────────

class NotificationViewSet(FirestoreViewSet):
    collection_name = 'hrm_notifications'
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]


class NotificationPreferenceViewSet(FirestoreViewSet):
    collection_name = 'hrm_notification_preferences'
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]


class DeviceTokenViewSet(FirestoreViewSet):
    collection_name = 'hrm_device_tokens'
    serializer_class = DeviceTokenSerializer
    permission_classes = [permissions.IsAuthenticated]


# ── Succession Planning ───────────────────────────────────────────────

class KeyPositionViewSet(FirestoreViewSet):
    collection_name = 'hrm_key_positions'
    serializer_class = KeyPositionSerializer
    permission_classes = [permissions.IsAuthenticated]


class SuccessorCandidateViewSet(FirestoreViewSet):
    collection_name = 'hrm_successor_candidates'
    serializer_class = SuccessorCandidateSerializer
    permission_classes = [permissions.IsAuthenticated]


class SuccessionPlanViewSet(FirestoreViewSet):
    collection_name = 'hrm_succession_plans'
    serializer_class = SuccessionPlanSerializer
    permission_classes = [permissions.IsAuthenticated]


# ── Employee Skills & Education ─────────────────────────────────────────────────

class EmployeeEducationViewSet(FirestoreViewSet):
    collection_name = 'hrm_employee_education'
    serializer_class = EmployeeEducationSerializer
    permission_classes = [permissions.IsAuthenticated]


class EmployeeExperienceViewSet(FirestoreViewSet):
    collection_name = 'hrm_employee_experience'
    serializer_class = EmployeeExperienceSerializer
    permission_classes = [permissions.IsAuthenticated]


class EmployeeSkillViewSet(FirestoreViewSet):
    collection_name = 'hrm_employee_skills'
    serializer_class = EmployeeSkillSerializer
    permission_classes = [permissions.IsAuthenticated]


class CompetencyViewSet(FirestoreViewSet):
    collection_name = 'hrm_competencies'
    serializer_class = CompetencySerializer
    permission_classes = [permissions.IsAuthenticated]


class CompetencyRatingViewSet(FirestoreViewSet):
    collection_name = 'hrm_competency_ratings'
    serializer_class = CompetencyRatingSerializer
    permission_classes = [permissions.IsAuthenticated]


class CandidateDocumentViewSet(FirestoreViewSet):
    collection_name = 'hrm_candidate_documents'
    serializer_class = CandidateDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]


# ── 360 Feedback ────────────────────────────────────────────────────────────────

class FeedbackQuestionViewSet(FirestoreViewSet):
    collection_name = 'hrm_feedback_questions'
    serializer_class = FeedbackQuestionSerializer
    permission_classes = [permissions.IsAuthenticated]


class FeedbackRequestViewSet(FirestoreViewSet):
    collection_name = 'hrm_feedback_requests'
    serializer_class = FeedbackRequestSerializer
    permission_classes = [permissions.IsAuthenticated]


class FeedbackResponseViewSet(FirestoreViewSet):
    collection_name = 'hrm_feedback_responses'
    serializer_class = FeedbackResponseSerializer
    permission_classes = [permissions.IsAuthenticated]


# ── Engagement Surveys ───────────────────────────────────────────────────────────

class EngagementSurveyViewSet(FirestoreViewSet):
    collection_name = 'hrm_engagement_surveys'
    serializer_class = EngagementSurveySerializer
    permission_classes = [permissions.IsAuthenticated]


class SurveyQuestionViewSet(FirestoreViewSet):
    collection_name = 'hrm_survey_questions'
    serializer_class = SurveyQuestionSerializer
    permission_classes = [permissions.IsAuthenticated]


class SurveyResponseViewSet(FirestoreViewSet):
    collection_name = 'hrm_survey_responses'
    serializer_class = SurveyResponseSerializer
    permission_classes = [permissions.IsAuthenticated]


# ── Compliance Calendar ──────────────────────────────────────────────────────────

class ComplianceReminderViewSet(FirestoreViewSet):
    collection_name = 'hrm_compliance_reminders'
    serializer_class = ComplianceReminderSerializer
    permission_classes = [permissions.IsAuthenticated]


# ── Talent Review & 9-Box ────────────────────────────────────────────────────────

class TalentReviewMeetingViewSet(FirestoreViewSet):
    collection_name = 'hrm_talent_review_meetings'
    serializer_class = TalentReviewMeetingSerializer
    permission_classes = [permissions.IsAuthenticated]


class NineBoxCellViewSet(FirestoreViewSet):
    collection_name = 'hrm_nine_box_cells'
    serializer_class = NineBoxCellSerializer
    permission_classes = [permissions.IsAuthenticated]


# ── Disciplinary Management ───────────────────────────────────────────────

class DisciplinaryCaseViewSet(FirestoreViewSet):
    collection_name = 'hrm_disciplinary_cases'
    serializer_class = DisciplinaryCaseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        from hrm.services.discipline import DisciplineService
        serializer.save(case_number=DisciplineService._next_case_number())


class DisciplinaryHearingViewSet(FirestoreViewSet):
    collection_name = 'hrm_disciplinary_hearings'
    serializer_class = DisciplinaryHearingSerializer
    permission_classes = [permissions.IsAuthenticated]


class DisciplinaryActionViewSet(FirestoreViewSet):
    collection_name = 'hrm_disciplinary_actions'
    serializer_class = DisciplinaryActionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(issued_by=self.request.user)


class DisciplinaryAppealViewSet(FirestoreViewSet):
    collection_name = 'hrm_disciplinary_appeals'
    serializer_class = DisciplinaryAppealSerializer
    permission_classes = [permissions.IsAuthenticated]
