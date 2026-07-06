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
