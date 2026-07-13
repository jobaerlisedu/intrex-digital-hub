from .base import ORMViewSet
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


class DepartmentViewSet(ORMViewSet):
    serializer_class = DepartmentSerializer


class PositionViewSet(ORMViewSet):
    serializer_class = PositionSerializer


class EmployeeViewSet(ORMViewSet):
    serializer_class = EmployeeSerializer
    filterset_fields = [
        'emp_id', 'department', 'position', 'employee_type',
        'status', 'gender', 'is_active',
    ]
    ordering_fields = [
        'emp_id', 'first_name', 'last_name', 'joining_date',
        'status', 'created_at', 'updated_at',
    ]


class RecruitmentCandidateViewSet(ORMViewSet):
    serializer_class = RecruitmentCandidateSerializer


class RecruitmentShortlistViewSet(ORMViewSet):
    serializer_class = RecruitmentShortlistSerializer


class RecruitmentInterviewViewSet(ORMViewSet):
    serializer_class = RecruitmentInterviewSerializer


class RecruitmentSelectionViewSet(ORMViewSet):
    serializer_class = RecruitmentSelectionSerializer


class AttendanceViewSet(ORMViewSet):
    serializer_class = AttendanceSerializer


class LeaveViewSet(ORMViewSet):
    serializer_class = LeaveSerializer


class HolidayViewSet(ORMViewSet):
    serializer_class = HolidaySerializer


class AdvanceSalaryViewSet(ORMViewSet):
    serializer_class = AdvanceSalarySerializer


class PayrollViewSet(ORMViewSet):
    serializer_class = PayrollSerializer


class PayrollEmployeeViewSet(ORMViewSet):
    serializer_class = PayrollEmployeeSerializer


class EmployeeShiftViewSet(ORMViewSet):
    serializer_class = EmployeeShiftSerializer


class OnboardingTaskViewSet(ORMViewSet):
    serializer_class = OnboardingTaskSerializer


class ExitClearanceViewSet(ORMViewSet):
    serializer_class = ExitClearanceSerializer


class ExpenseClaimViewSet(ORMViewSet):
    serializer_class = ExpenseClaimSerializer


class DocumentViewSet(ORMViewSet):
    serializer_class = DocumentSerializer


class AssetViewSet(ORMViewSet):
    serializer_class = AssetSerializer


class HRMSettingViewSet(ORMViewSet):
    serializer_class = HRMSettingSerializer


# -- Performance Management -------------------------------------------------


class ReviewCycleViewSet(ORMViewSet):
    serializer_class = ReviewCycleSerializer


class RatingTemplateViewSet(ORMViewSet):
    serializer_class = RatingTemplateSerializer


class RatingScaleViewSet(ORMViewSet):
    serializer_class = RatingScaleSerializer


class KPIViewSet(ORMViewSet):
    serializer_class = KPISerializer


class EmployeeKPIViewSet(ORMViewSet):
    serializer_class = EmployeeKPISerializer


class PerformanceReviewViewSet(ORMViewSet):
    serializer_class = PerformanceReviewSerializer


class PerformanceImprovementPlanViewSet(ORMViewSet):
    serializer_class = PerformanceImprovementPlanSerializer


class PIPMilestoneViewSet(ORMViewSet):
    serializer_class = PIPMilestoneSerializer


# -- Leave Balance -----------------------------------------------------------


class LeavePolicyViewSet(ORMViewSet):
    serializer_class = LeavePolicySerializer


class LeaveBalanceViewSet(ORMViewSet):
    serializer_class = LeaveBalanceSerializer


# -- Training & Development --------------------------------------------------


class TrainingNeedViewSet(ORMViewSet):
    serializer_class = TrainingNeedSerializer


class DevelopmentPlanViewSet(ORMViewSet):
    serializer_class = DevelopmentPlanSerializer


class TrainingNominationViewSet(ORMViewSet):
    serializer_class = TrainingNominationSerializer


# -- Notifications -----------------------------------------------------------


class NotificationViewSet(ORMViewSet):
    serializer_class = NotificationSerializer


class NotificationPreferenceViewSet(ORMViewSet):
    serializer_class = NotificationPreferenceSerializer


class DeviceTokenViewSet(ORMViewSet):
    serializer_class = DeviceTokenSerializer


# -- Succession Planning -----------------------------------------------------


class KeyPositionViewSet(ORMViewSet):
    serializer_class = KeyPositionSerializer


class SuccessorCandidateViewSet(ORMViewSet):
    serializer_class = SuccessorCandidateSerializer


class SuccessionPlanViewSet(ORMViewSet):
    serializer_class = SuccessionPlanSerializer


# -- Employee Skills & Education ---------------------------------------------


class EmployeeEducationViewSet(ORMViewSet):
    serializer_class = EmployeeEducationSerializer


class EmployeeExperienceViewSet(ORMViewSet):
    serializer_class = EmployeeExperienceSerializer


class EmployeeSkillViewSet(ORMViewSet):
    serializer_class = EmployeeSkillSerializer


class CompetencyViewSet(ORMViewSet):
    serializer_class = CompetencySerializer


class CompetencyRatingViewSet(ORMViewSet):
    serializer_class = CompetencyRatingSerializer


class CandidateDocumentViewSet(ORMViewSet):
    serializer_class = CandidateDocumentSerializer


# -- 360 Feedback ------------------------------------------------------------


class FeedbackQuestionViewSet(ORMViewSet):
    serializer_class = FeedbackQuestionSerializer


class FeedbackRequestViewSet(ORMViewSet):
    serializer_class = FeedbackRequestSerializer


class FeedbackResponseViewSet(ORMViewSet):
    serializer_class = FeedbackResponseSerializer


# -- Engagement Surveys ------------------------------------------------------


class EngagementSurveyViewSet(ORMViewSet):
    serializer_class = EngagementSurveySerializer


class SurveyQuestionViewSet(ORMViewSet):
    serializer_class = SurveyQuestionSerializer


class SurveyResponseViewSet(ORMViewSet):
    serializer_class = SurveyResponseSerializer


# -- Compliance Calendar -----------------------------------------------------


class ComplianceReminderViewSet(ORMViewSet):
    serializer_class = ComplianceReminderSerializer


# -- Talent Review & 9-Box --------------------------------------------------


class TalentReviewMeetingViewSet(ORMViewSet):
    serializer_class = TalentReviewMeetingSerializer


class NineBoxCellViewSet(ORMViewSet):
    serializer_class = NineBoxCellSerializer


# -- Disciplinary Management -------------------------------------------------


class DisciplinaryCaseViewSet(ORMViewSet):
    serializer_class = DisciplinaryCaseSerializer

    def perform_create(self, serializer):
        from hrm.services.discipline import DisciplineService
        serializer.save(case_number=DisciplineService._next_case_number())


class DisciplinaryHearingViewSet(ORMViewSet):
    serializer_class = DisciplinaryHearingSerializer


class DisciplinaryActionViewSet(ORMViewSet):
    serializer_class = DisciplinaryActionSerializer

    def perform_create(self, serializer):
        serializer.save(issued_by=self.request.user)


class DisciplinaryAppealViewSet(ORMViewSet):
    serializer_class = DisciplinaryAppealSerializer
