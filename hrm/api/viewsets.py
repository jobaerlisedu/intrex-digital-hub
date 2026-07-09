from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend
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


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = models.Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['name', 'status', 'is_active']
    search_fields = ['name', 'notes']
    ordering_fields = ['name', 'status', 'created_at', 'updated_at']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class PositionViewSet(viewsets.ModelViewSet):
    queryset = models.Position.objects.all()
    serializer_class = PositionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['title', 'department', 'status', 'is_active']
    search_fields = ['title']
    ordering_fields = ['title', 'status', 'created_at', 'updated_at']


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = models.Employee.objects.all()
    serializer_class = EmployeeSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        'emp_id', 'department', 'position', 'employee_type',
        'status', 'gender', 'is_active',
    ]
    search_fields = ['emp_id', 'first_name', 'last_name', 'email', 'phone']
    ordering_fields = [
        'emp_id', 'first_name', 'last_name', 'joining_date',
        'status', 'created_at', 'updated_at',
    ]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class RecruitmentCandidateViewSet(viewsets.ModelViewSet):
    queryset = models.RecruitmentCandidate.objects.all()
    serializer_class = RecruitmentCandidateSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['cand_id', 'position', 'status', 'is_active']
    search_fields = ['cand_id', 'name', 'position', 'notes']
    ordering_fields = ['cand_id', 'name', 'position', 'status', 'date_applied', 'created_at', 'updated_at']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class RecruitmentShortlistViewSet(viewsets.ModelViewSet):
    queryset = models.RecruitmentShortlist.objects.all()
    serializer_class = RecruitmentShortlistSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['candidate', 'position', 'rating', 'is_active']
    search_fields = ['name', 'position', 'rating', 'experience']
    ordering_fields = ['name', 'position', 'rating', 'created_at', 'updated_at']


class RecruitmentInterviewViewSet(viewsets.ModelViewSet):
    queryset = models.RecruitmentInterview.objects.all()
    serializer_class = RecruitmentInterviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['candidate', 'position', 'interviewer', 'status', 'is_active']
    search_fields = ['name', 'position', 'interviewer']
    ordering_fields = ['name', 'position', 'date_time', 'status', 'created_at', 'updated_at']


class RecruitmentSelectionViewSet(viewsets.ModelViewSet):
    queryset = models.RecruitmentSelection.objects.all()
    serializer_class = RecruitmentSelectionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['candidate', 'position', 'offer_status', 'is_active']
    search_fields = ['name', 'position']
    ordering_fields = ['name', 'position', 'offer_status', 'offer_date', 'created_at', 'updated_at']


class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = models.Attendance.objects.all()
    serializer_class = AttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'date', 'status', 'resolved', 'is_active']
    search_fields = []
    ordering_fields = ['date', 'check_in', 'check_out', 'status', 'created_at', 'updated_at']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class LeaveViewSet(viewsets.ModelViewSet):
    queryset = models.Leave.objects.all()
    serializer_class = LeaveSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'leave_type', 'from_date', 'to_date', 'status', 'is_active']
    search_fields = ['reason']
    ordering_fields = ['leave_type', 'from_date', 'to_date', 'status', 'created_at', 'updated_at']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class HolidayViewSet(viewsets.ModelViewSet):
    queryset = models.Holiday.objects.all()
    serializer_class = HolidaySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['holiday_name', 'holiday_type', 'is_active']
    search_fields = ['holiday_name']
    ordering_fields = ['holiday_name', 'from_date', 'to_date', 'holiday_type', 'created_at', 'updated_at']


class AdvanceSalaryViewSet(viewsets.ModelViewSet):
    queryset = models.AdvanceSalary.objects.all()
    serializer_class = AdvanceSalarySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'deduct_month', 'status', 'is_active']
    search_fields = ['reason']
    ordering_fields = ['amount', 'deduct_month', 'status', 'created_at', 'updated_at']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class PayrollViewSet(viewsets.ModelViewSet):
    queryset = models.Payroll.objects.all()
    serializer_class = PayrollSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['period', 'status', 'is_active']
    search_fields = ['period']
    ordering_fields = ['period', 'employee_count', 'total_net_pay', 'status', 'created_at', 'updated_at']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class PayrollEmployeeViewSet(viewsets.ModelViewSet):
    queryset = models.PayrollEmployee.objects.all()
    serializer_class = PayrollEmployeeSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['payroll', 'employee']
    search_fields = []
    ordering_fields = ['basic_salary', 'gross_pay', 'net_pay', 'created_at']


class EmployeeShiftViewSet(viewsets.ModelViewSet):
    queryset = models.EmployeeShift.objects.all()
    serializer_class = EmployeeShiftSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'shift_name', 'is_active']
    search_fields = ['shift_name']
    ordering_fields = ['shift_name', 'start_date', 'end_date', 'created_at', 'updated_at']


class OnboardingTaskViewSet(viewsets.ModelViewSet):
    queryset = models.OnboardingTask.objects.all()
    serializer_class = OnboardingTaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'task_name', 'due_date', 'status', 'is_active']
    search_fields = ['task_name']
    ordering_fields = ['task_name', 'due_date', 'status', 'created_at', 'updated_at']


class ExitClearanceViewSet(viewsets.ModelViewSet):
    queryset = models.ExitClearance.objects.all()
    serializer_class = ExitClearanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'exit_date', 'it_clearance', 'finance_clearance', 'hr_clearance', 'status', 'is_active']
    search_fields = ['reason']
    ordering_fields = ['exit_date', 'status', 'created_at', 'updated_at']


class ExpenseClaimViewSet(viewsets.ModelViewSet):
    queryset = models.ExpenseClaim.objects.all()
    serializer_class = ExpenseClaimSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'category', 'amount', 'status', 'is_active']
    search_fields = ['category', 'description']
    ordering_fields = ['category', 'amount', 'status', 'created_at', 'updated_at']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class DocumentViewSet(viewsets.ModelViewSet):
    queryset = models.Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'document_type', 'document_number', 'is_active']
    search_fields = ['document_type', 'document_number']
    ordering_fields = ['document_type', 'expiry_date', 'created_at', 'updated_at']


class AssetViewSet(viewsets.ModelViewSet):
    queryset = models.Asset.objects.all()
    serializer_class = AssetSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'asset_name', 'asset_tag', 'status', 'is_active']
    search_fields = ['asset_name', 'asset_tag', 'serial_number']
    ordering_fields = ['asset_name', 'status', 'created_at', 'updated_at']


class HRMSettingViewSet(viewsets.ModelViewSet):
    queryset = models.HRMSetting.objects.all()
    serializer_class = HRMSettingSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['key', 'is_active']
    search_fields = ['key']
    ordering_fields = ['key', 'created_at', 'updated_at']


# ── Performance Management ─────────────────────────────────────────────

class ReviewCycleViewSet(viewsets.ModelViewSet):
    queryset = models.ReviewCycle.objects.all()
    serializer_class = ReviewCycleSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['name', 'review_type', 'status', 'is_active']
    search_fields = ['name']
    ordering_fields = ['start_date', 'end_date', 'created_at']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class RatingTemplateViewSet(viewsets.ModelViewSet):
    queryset = models.RatingTemplate.objects.all()
    serializer_class = RatingTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['name', 'is_active']
    search_fields = ['name']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class RatingScaleViewSet(viewsets.ModelViewSet):
    queryset = models.RatingScale.objects.all()
    serializer_class = RatingScaleSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['template', 'label', 'is_active']
    ordering_fields = ['template', 'order', 'value']


class KPIViewSet(viewsets.ModelViewSet):
    queryset = models.KPI.objects.all()
    serializer_class = KPISerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['name', 'unit', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']


class EmployeeKPIViewSet(viewsets.ModelViewSet):
    queryset = models.EmployeeKPI.objects.all()
    serializer_class = EmployeeKPISerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'review_cycle', 'kpi', 'is_active']
    search_fields = ['comments']
    ordering_fields = ['employee', 'review_cycle', 'target_value', 'score']


class PerformanceReviewViewSet(viewsets.ModelViewSet):
    queryset = models.PerformanceReview.objects.all()
    serializer_class = PerformanceReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'reviewer', 'review_cycle', 'status', 'is_active']
    search_fields = ['strengths', 'improvements', 'goals']
    ordering_fields = ['overall_score', 'status', 'created_at']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class PerformanceImprovementPlanViewSet(viewsets.ModelViewSet):
    queryset = models.PerformanceImprovementPlan.objects.all()
    serializer_class = PerformanceImprovementPlanSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'review', 'status', 'is_active']
    search_fields = ['issue_description', 'improvement_goals']
    ordering_fields = ['start_date', 'end_date', 'created_at']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class PIPMilestoneViewSet(viewsets.ModelViewSet):
    queryset = models.PIPMilestone.objects.all()
    serializer_class = PIPMilestoneSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['pip', 'status', 'is_active']
    ordering_fields = ['pip', 'due_date', 'created_at']


# ── Leave Balance ──────────────────────────────────────────────────────

class LeavePolicyViewSet(viewsets.ModelViewSet):
    queryset = models.LeavePolicy.objects.all()
    serializer_class = LeavePolicySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee_type', 'leave_type', 'is_active']
    ordering_fields = ['employee_type', 'leave_type', 'entitled_days']


class LeaveBalanceViewSet(viewsets.ModelViewSet):
    queryset = models.LeaveBalance.objects.all()
    serializer_class = LeaveBalanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'leave_type', 'period', 'is_active']
    ordering_fields = ['employee', 'leave_type', 'entitled', 'used', 'available']


# ── Training & Development ─────────────────────────────────────────────

class TrainingNeedViewSet(viewsets.ModelViewSet):
    queryset = models.TrainingNeed.objects.all()
    serializer_class = TrainingNeedSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'skill_gap', 'priority', 'status', 'is_active']
    search_fields = ['skill_gap', 'recommended_training', 'notes']
    ordering_fields = ['employee', 'priority', 'status', 'created_at']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class DevelopmentPlanViewSet(viewsets.ModelViewSet):
    queryset = models.DevelopmentPlan.objects.all()
    serializer_class = DevelopmentPlanSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'status', 'is_active']
    search_fields = ['title', 'description', 'goals']
    ordering_fields = ['employee', 'start_date', 'target_end_date', 'status']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class TrainingNominationViewSet(viewsets.ModelViewSet):
    queryset = models.TrainingNomination.objects.all()
    serializer_class = TrainingNominationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'course_name', 'status', 'is_active']
    search_fields = ['course_name', 'provider', 'notes']
    ordering_fields = ['employee', 'start_date', 'status', 'created_at']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


# ── Notifications ─────────────────────────────────────────────────────

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = models.Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['recipient', 'notification_type', 'is_read', 'channel', 'is_active']
    ordering_fields = ['-created_at']

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_superuser and not self.request.user.is_staff:
            qs = qs.filter(recipient=self.request.user)
        return qs


class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    queryset = models.NotificationPreference.objects.all()
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['user']

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_superuser and not self.request.user.is_staff:
            qs = qs.filter(user=self.request.user)
        return qs


class DeviceTokenViewSet(viewsets.ModelViewSet):
    queryset = models.DeviceToken.objects.all()
    serializer_class = DeviceTokenSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['user', 'platform', 'is_active']


# ── Succession Planning ───────────────────────────────────────────────

class KeyPositionViewSet(viewsets.ModelViewSet):
    queryset = models.KeyPosition.objects.all()
    serializer_class = KeyPositionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['position', 'department', 'risk_of_vacancy', 'status', 'is_active']
    search_fields = ['position_title', 'readiness_gap']
    ordering_fields = ['position_title', 'risk_of_vacancy', 'status']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class SuccessorCandidateViewSet(viewsets.ModelViewSet):
    queryset = models.SuccessorCandidate.objects.all()
    serializer_class = SuccessorCandidateSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['key_position', 'employee', 'readiness', 'is_primary', 'is_active']
    search_fields = ['strengths', 'development_needs', 'notes']
    ordering_fields = ['key_position', 'readiness', 'employee']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class SuccessionPlanViewSet(viewsets.ModelViewSet):
    queryset = models.SuccessionPlan.objects.all()
    serializer_class = SuccessionPlanSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['department', 'status', 'is_active']
    search_fields = ['title', 'description']
    ordering_fields = ['title', 'review_date', 'status']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


# ── Employee Skills & Education ─────────────────────────────────────────────────

class EmployeeEducationViewSet(viewsets.ModelViewSet):
    queryset = models.EmployeeEducation.objects.all()
    serializer_class = EmployeeEducationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'degree', 'is_active']
    ordering_fields = ['-end_year']


class EmployeeExperienceViewSet(viewsets.ModelViewSet):
    queryset = models.EmployeeExperience.objects.all()
    serializer_class = EmployeeExperienceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'is_current', 'is_active']
    ordering_fields = ['-start_date']


class EmployeeSkillViewSet(viewsets.ModelViewSet):
    queryset = models.EmployeeSkill.objects.all()
    serializer_class = EmployeeSkillSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'proficiency', 'is_active']
    search_fields = ['skill_name']
    ordering_fields = ['skill_name']


class CompetencyViewSet(viewsets.ModelViewSet):
    queryset = models.Competency.objects.all()
    serializer_class = CompetencySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category', 'is_active']
    search_fields = ['name']
    ordering_fields = ['category', 'name']


class CompetencyRatingViewSet(viewsets.ModelViewSet):
    queryset = models.CompetencyRating.objects.all()
    serializer_class = CompetencyRatingSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'competency', 'rating', 'is_active']
    ordering_fields = ['-assessment_date']


class CandidateDocumentViewSet(viewsets.ModelViewSet):
    queryset = models.CandidateDocument.objects.all()
    serializer_class = CandidateDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['candidate', 'document_type']


# ── 360 Feedback ────────────────────────────────────────────────────────────────

class FeedbackQuestionViewSet(viewsets.ModelViewSet):
    queryset = models.FeedbackQuestion.objects.all()
    serializer_class = FeedbackQuestionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category', 'is_required', 'is_active']
    ordering_fields = ['category', 'order']


class FeedbackRequestViewSet(viewsets.ModelViewSet):
    queryset = models.FeedbackRequest.objects.all()
    serializer_class = FeedbackRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['reviewer', 'reviewee', 'review_cycle', 'relationship', 'status', 'is_active']
    ordering_fields = ['-created_at']


class FeedbackResponseViewSet(viewsets.ModelViewSet):
    queryset = models.FeedbackResponse.objects.all()
    serializer_class = FeedbackResponseSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['request', 'question']


# ── Engagement Surveys ───────────────────────────────────────────────────────────

class EngagementSurveyViewSet(viewsets.ModelViewSet):
    queryset = models.EngagementSurvey.objects.all()
    serializer_class = EngagementSurveySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'is_anonymous', 'is_active']
    search_fields = ['title']
    ordering_fields = ['-created_at']


class SurveyQuestionViewSet(viewsets.ModelViewSet):
    queryset = models.SurveyQuestion.objects.all()
    serializer_class = SurveyQuestionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['survey', 'question_type', 'is_required', 'is_active']
    ordering_fields = ['survey', 'order']


class SurveyResponseViewSet(viewsets.ModelViewSet):
    queryset = models.SurveyResponse.objects.all()
    serializer_class = SurveyResponseSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['survey', 'question', 'employee']


# ── Compliance Calendar ──────────────────────────────────────────────────────────

class ComplianceReminderViewSet(viewsets.ModelViewSet):
    queryset = models.ComplianceReminder.objects.all()
    serializer_class = ComplianceReminderSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'reminder_type', 'status', 'is_active']
    ordering_fields = ['due_date']


# ── Talent Review & 9-Box ────────────────────────────────────────────────────────

class TalentReviewMeetingViewSet(viewsets.ModelViewSet):
    queryset = models.TalentReviewMeeting.objects.all()
    serializer_class = TalentReviewMeetingSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'is_active']
    search_fields = ['title']
    ordering_fields = ['-meeting_date']


class NineBoxCellViewSet(viewsets.ModelViewSet):
    queryset = models.NineBoxCell.objects.all()
    serializer_class = NineBoxCellSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['talent_review', 'employee', 'performance', 'potential', 'is_active']
    ordering_fields = ['talent_review', 'employee']


# ── Disciplinary Management ───────────────────────────────────────────────

class DisciplinaryCaseViewSet(viewsets.ModelViewSet):
    queryset = models.DisciplinaryCase.objects.filter(is_active=True).select_related('employee', 'reported_by')
    serializer_class = DisciplinaryCaseSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'severity', 'status', 'is_active']
    search_fields = ['case_number', 'nature_of_offense', 'description']
    ordering_fields = ['-created_at', '-incident_date', 'severity', 'status']

    def perform_create(self, serializer):
        serializer.save(reported_by=self.request.user, created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class DisciplinaryHearingViewSet(viewsets.ModelViewSet):
    queryset = models.DisciplinaryHearing.objects.filter(is_active=True).select_related('case')
    serializer_class = DisciplinaryHearingSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['case', 'status', 'is_active']
    ordering_fields = ['-hearing_date', 'status']


class DisciplinaryActionViewSet(viewsets.ModelViewSet):
    queryset = models.DisciplinaryAction.objects.filter(is_active=True).select_related('case', 'issued_by')
    serializer_class = DisciplinaryActionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['case', 'action_type', 'status', 'is_active']
    search_fields = ['description']
    ordering_fields = ['-issued_date', '-effective_date', 'action_type']

    def perform_create(self, serializer):
        serializer.save(issued_by=self.request.user)


class DisciplinaryAppealViewSet(viewsets.ModelViewSet):
    queryset = models.DisciplinaryAppeal.objects.filter(is_active=True).select_related('action', 'decided_by')
    serializer_class = DisciplinaryAppealSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['action', 'status', 'is_active']
    ordering_fields = ['-appeal_date', 'status']

    def perform_update(self, serializer):
        serializer.save(decided_by=self.request.user)
