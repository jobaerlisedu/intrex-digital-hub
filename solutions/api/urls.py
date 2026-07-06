from django.urls import path, include
from rest_framework.routers import DefaultRouter
from solutions.api.viewsets import (
    ProjectViewSet,
    ProjectPhaseViewSet,
    TaskViewSet,
    ProjectRequisitionViewSet,
    SoftwareLicenseViewSet,
    ProjectStakeholderViewSet,
    MeetingViewSet,
)

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='solutions-project')
router.register(r'project-phases', ProjectPhaseViewSet, basename='solutions-projectphase')
router.register(r'tasks', TaskViewSet, basename='solutions-task')
router.register(r'project-requisitions', ProjectRequisitionViewSet, basename='solutions-projectrequisition')
router.register(r'software-licenses', SoftwareLicenseViewSet, basename='solutions-softwarelicense')
router.register(r'project-stakeholders', ProjectStakeholderViewSet, basename='solutions-projectstakeholder')
router.register(r'meetings', MeetingViewSet, basename='solutions-meeting')

urlpatterns = [
    path('', include(router.urls)),
]
