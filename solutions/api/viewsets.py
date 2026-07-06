from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from solutions.models import Project, ProjectPhase, Task, ProjectRequisition, SoftwareLicense, ProjectStakeholder, Meeting
from solutions.api.serializers import (
    ProjectSerializer,
    ProjectPhaseSerializer,
    TaskSerializer,
    ProjectRequisitionSerializer,
    SoftwareLicenseSerializer,
    ProjectStakeholderSerializer,
    MeetingSerializer,
)


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'category', 'is_active']
    search_fields = ['name', 'project_code', 'client_name']
    ordering_fields = '__all__'

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class ProjectPhaseViewSet(viewsets.ModelViewSet):
    queryset = ProjectPhase.objects.all()
    serializer_class = ProjectPhaseSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project', 'status', 'is_active']
    search_fields = ['phase_name']
    ordering_fields = '__all__'

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['phase', 'priority', 'status', 'assigned_to', 'is_active']
    search_fields = ['task_name', 'assigned_to']
    ordering_fields = '__all__'

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class ProjectRequisitionViewSet(viewsets.ModelViewSet):
    queryset = ProjectRequisition.objects.all()
    serializer_class = ProjectRequisitionSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project', 'phase', 'status', 'is_active']
    search_fields = ['item_name', 'requisition_ref']
    ordering_fields = '__all__'

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class SoftwareLicenseViewSet(viewsets.ModelViewSet):
    queryset = SoftwareLicense.objects.all()
    serializer_class = SoftwareLicenseSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project', 'subscription_tier', 'status', 'is_active']
    search_fields = ['license_name', 'license_key']
    ordering_fields = '__all__'

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()


class ProjectStakeholderViewSet(viewsets.ModelViewSet):
    queryset = ProjectStakeholder.objects.all()
    serializer_class = ProjectStakeholderSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project', 'role', 'is_active']
    search_fields = ['contact_name', 'email']
    ordering_fields = '__all__'

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()


class MeetingViewSet(viewsets.ModelViewSet):
    queryset = Meeting.objects.all()
    serializer_class = MeetingSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project', 'is_active']
    search_fields = ['title']
    ordering_fields = '__all__'

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
