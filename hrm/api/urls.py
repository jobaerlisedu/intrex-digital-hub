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

urlpatterns = router.urls
