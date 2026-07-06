from rest_framework import viewsets

from training.api.serializers import (
    AmbassadorSerializer,
    AssessmentSerializer,
    BatchSerializer,
    CertificateSerializer,
    ClassSessionSerializer,
    CommissionSerializer,
    CourseSerializer,
    ExpenseSerializer,
    InquirySerializer,
    InstituteSerializer,
    JobPlacementSerializer,
    PaymentSerializer,
    RegistrationSerializer,
)
from training.models import (
    Ambassador,
    Assessment,
    Batch,
    Certificate,
    ClassSession,
    Commission,
    Course,
    Expense,
    Inquiry,
    Institute,
    JobPlacement,
    Payment,
    Registration,
)


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    search_fields = ['title', 'code']
    filterset_fields = ['status', 'is_active']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class BatchViewSet(viewsets.ModelViewSet):
    queryset = Batch.objects.all()
    serializer_class = BatchSerializer
    search_fields = ['batch_id', 'course__title']
    filterset_fields = ['status', 'is_active', 'course']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class RegistrationViewSet(viewsets.ModelViewSet):
    queryset = Registration.objects.select_related(
        'payment', 'assessment', 'course', 'batch'
    ).prefetch_related('certificates').all()
    serializer_class = RegistrationSerializer
    search_fields = ['full_name', 'student_id', 'email', 'phone']
    filterset_fields = ['is_active', 'course', 'batch', 'is_job_holder', 'is_free_batch']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    search_fields = ['student_id', 'student_name', 'transaction_id']
    filterset_fields = ['status', 'payment_type', 'is_active']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer
    search_fields = ['category', 'description']
    filterset_fields = ['category', 'payment_method', 'is_active']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class InquiryViewSet(viewsets.ModelViewSet):
    queryset = Inquiry.objects.all()
    serializer_class = InquirySerializer
    search_fields = ['name', 'email', 'phone', 'subject']
    filterset_fields = ['source', 'status', 'is_active']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class InstituteViewSet(viewsets.ModelViewSet):
    queryset = Institute.objects.all()
    serializer_class = InstituteSerializer
    search_fields = ['name', 'email', 'phone', 'contact_person']
    filterset_fields = ['institute_type', 'status', 'is_active']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class AmbassadorViewSet(viewsets.ModelViewSet):
    queryset = Ambassador.objects.all()
    serializer_class = AmbassadorSerializer
    search_fields = ['name', 'email', 'phone', 'region']
    filterset_fields = ['status', 'is_active']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class CommissionViewSet(viewsets.ModelViewSet):
    queryset = Commission.objects.select_related('agent').all()
    serializer_class = CommissionSerializer
    search_fields = ['agent_name', 'month', 'year']
    filterset_fields = ['status', 'is_active', 'agent']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class AssessmentViewSet(viewsets.ModelViewSet):
    queryset = Assessment.objects.all()
    serializer_class = AssessmentSerializer
    search_fields = ['student_id', 'student_name', 'course_name']
    filterset_fields = ['grade', 'status', 'is_active']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class CertificateViewSet(viewsets.ModelViewSet):
    queryset = Certificate.objects.all()
    serializer_class = CertificateSerializer
    search_fields = ['certificate_id', 'student_id', 'student_name', 'course_name']
    filterset_fields = ['status', 'is_active']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class JobPlacementViewSet(viewsets.ModelViewSet):
    queryset = JobPlacement.objects.all()
    serializer_class = JobPlacementSerializer
    search_fields = ['student_id', 'student_name', 'company', 'job_title']
    filterset_fields = ['placement_type', 'is_active']

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()


class ClassSessionViewSet(viewsets.ModelViewSet):
    queryset = ClassSession.objects.all()
    serializer_class = ClassSessionSerializer
    search_fields = ['class_title', 'course__title']
    filterset_fields = ['is_active', 'course']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
