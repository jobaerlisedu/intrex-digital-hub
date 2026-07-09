from rest_framework import routers
from .viewsets import (
    DepartmentViewSet,
    PositionViewSet,
    EmployeeViewSet,
    RecruitmentCandidateViewSet,
    RecruitmentShortlistViewSet,
    RecruitmentInterviewViewSet,
    RecruitmentSelectionViewSet,
    AttendanceViewSet,
    LeaveViewSet,
    HolidayViewSet,
    AdvanceSalaryViewSet,
    PayrollViewSet,
    PayrollEmployeeViewSet,
    EmployeeShiftViewSet,
    OnboardingTaskViewSet,
    ExitClearanceViewSet,
    ExpenseClaimViewSet,
    DocumentViewSet,
    AssetViewSet,
    HRMSettingViewSet,
    ReviewCycleViewSet,
    RatingTemplateViewSet,
    RatingScaleViewSet,
    KPIViewSet,
    EmployeeKPIViewSet,
    PerformanceReviewViewSet,
    PerformanceImprovementPlanViewSet,
    PIPMilestoneViewSet,
    LeavePolicyViewSet,
    LeaveBalanceViewSet,
    TrainingNeedViewSet,
    DevelopmentPlanViewSet,
    TrainingNominationViewSet,
    NotificationViewSet,
    NotificationPreferenceViewSet,
    DeviceTokenViewSet,
    KeyPositionViewSet,
    SuccessorCandidateViewSet,
    SuccessionPlanViewSet,
    EmployeeEducationViewSet,
    EmployeeExperienceViewSet,
    EmployeeSkillViewSet,
    CompetencyViewSet,
    CompetencyRatingViewSet,
    CandidateDocumentViewSet,
    FeedbackQuestionViewSet,
    FeedbackRequestViewSet,
    FeedbackResponseViewSet,
    EngagementSurveyViewSet,
    SurveyQuestionViewSet,
    SurveyResponseViewSet,
    ComplianceReminderViewSet,
    TalentReviewMeetingViewSet,
    NineBoxCellViewSet,
)

router = routers.DefaultRouter()
router.register(r'departments', DepartmentViewSet, basename='hrm-department')
router.register(r'positions', PositionViewSet, basename='hrm-position')
router.register(r'employees', EmployeeViewSet, basename='hrm-employee')
router.register(r'recruitment-candidates', RecruitmentCandidateViewSet, basename='hrm-recruitment-candidate')
router.register(r'recruitment-shortlists', RecruitmentShortlistViewSet, basename='hrm-recruitment-shortlist')
router.register(r'recruitment-interviews', RecruitmentInterviewViewSet, basename='hrm-recruitment-interview')
router.register(r'recruitment-selections', RecruitmentSelectionViewSet, basename='hrm-recruitment-selection')
router.register(r'attendance', AttendanceViewSet, basename='hrm-attendance')
router.register(r'leaves', LeaveViewSet, basename='hrm-leave')
router.register(r'holidays', HolidayViewSet, basename='hrm-holiday')
router.register(r'advance-salaries', AdvanceSalaryViewSet, basename='hrm-advance-salary')
router.register(r'payrolls', PayrollViewSet, basename='hrm-payroll')
router.register(r'payroll-employees', PayrollEmployeeViewSet, basename='hrm-payroll-employee')
router.register(r'employee-shifts', EmployeeShiftViewSet, basename='hrm-employee-shift')
router.register(r'onboarding-tasks', OnboardingTaskViewSet, basename='hrm-onboarding-task')
router.register(r'exit-clearances', ExitClearanceViewSet, basename='hrm-exit-clearance')
router.register(r'expense-claims', ExpenseClaimViewSet, basename='hrm-expense-claim')
router.register(r'documents', DocumentViewSet, basename='hrm-document')
router.register(r'assets', AssetViewSet, basename='hrm-asset')
router.register(r'settings', HRMSettingViewSet, basename='hrm-setting')
router.register(r'review-cycles', ReviewCycleViewSet, basename='hrm-review-cycle')
router.register(r'rating-templates', RatingTemplateViewSet, basename='hrm-rating-template')
router.register(r'rating-scales', RatingScaleViewSet, basename='hrm-rating-scale')
router.register(r'kpis', KPIViewSet, basename='hrm-kpi')
router.register(r'employee-kpis', EmployeeKPIViewSet, basename='hrm-employee-kpi')
router.register(r'performance-reviews', PerformanceReviewViewSet, basename='hrm-performance-review')
router.register(r'performance-improvement-plans', PerformanceImprovementPlanViewSet, basename='hrm-pip')
router.register(r'pip-milestones', PIPMilestoneViewSet, basename='hrm-pip-milestone')
router.register(r'leave-policies', LeavePolicyViewSet, basename='hrm-leave-policy')
router.register(r'leave-balances', LeaveBalanceViewSet, basename='hrm-leave-balance')
router.register(r'training-needs', TrainingNeedViewSet, basename='hrm-training-need')
router.register(r'development-plans', DevelopmentPlanViewSet, basename='hrm-development-plan')
router.register(r'training-nominations', TrainingNominationViewSet, basename='hrm-training-nomination')
router.register(r'notifications', NotificationViewSet, basename='hrm-notification')
router.register(r'notification-preferences', NotificationPreferenceViewSet, basename='hrm-notification-preference')
router.register(r'device-tokens', DeviceTokenViewSet, basename='hrm-device-token')
router.register(r'key-positions', KeyPositionViewSet, basename='hrm-key-position')
router.register(r'successor-candidates', SuccessorCandidateViewSet, basename='hrm-successor-candidate')
router.register(r'succession-plans', SuccessionPlanViewSet, basename='hrm-succession-plan')
router.register(r'employee-education', EmployeeEducationViewSet, basename='hrm-employee-education')
router.register(r'employee-experience', EmployeeExperienceViewSet, basename='hrm-employee-experience')
router.register(r'employee-skills', EmployeeSkillViewSet, basename='hrm-employee-skill')
router.register(r'competencies', CompetencyViewSet, basename='hrm-competency')
router.register(r'competency-ratings', CompetencyRatingViewSet, basename='hrm-competency-rating')
router.register(r'candidate-documents', CandidateDocumentViewSet, basename='hrm-candidate-document')
router.register(r'feedback-questions', FeedbackQuestionViewSet, basename='hrm-feedback-question')
router.register(r'feedback-requests', FeedbackRequestViewSet, basename='hrm-feedback-request')
router.register(r'feedback-responses', FeedbackResponseViewSet, basename='hrm-feedback-response')
router.register(r'engagement-surveys', EngagementSurveyViewSet, basename='hrm-engagement-survey')
router.register(r'survey-questions', SurveyQuestionViewSet, basename='hrm-survey-question')
router.register(r'survey-responses', SurveyResponseViewSet, basename='hrm-survey-response')
router.register(r'compliance-reminders', ComplianceReminderViewSet, basename='hrm-compliance-reminder')
router.register(r'talent-review-meetings', TalentReviewMeetingViewSet, basename='hrm-talent-review-meeting')
router.register(r'nine-box-cells', NineBoxCellViewSet, basename='hrm-nine-box-cell')

urlpatterns = router.urls
