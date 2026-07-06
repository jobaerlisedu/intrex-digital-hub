from django.urls import include, path
from rest_framework.routers import DefaultRouter

from training.api.viewsets import (
    AmbassadorViewSet,
    AssessmentViewSet,
    BatchViewSet,
    CertificateViewSet,
    ClassSessionViewSet,
    CommissionViewSet,
    CourseViewSet,
    ExpenseViewSet,
    InquiryViewSet,
    InstituteViewSet,
    JobPlacementViewSet,
    PaymentViewSet,
    RegistrationViewSet,
)

router = DefaultRouter()
router.register(r'courses', CourseViewSet, basename='training-course')
router.register(r'batches', BatchViewSet, basename='training-batch')
router.register(r'registrations', RegistrationViewSet, basename='training-registration')
router.register(r'payments', PaymentViewSet, basename='training-payment')
router.register(r'expenses', ExpenseViewSet, basename='training-expense')
router.register(r'inquiries', InquiryViewSet, basename='training-inquiry')
router.register(r'institutes', InstituteViewSet, basename='training-institute')
router.register(r'ambassadors', AmbassadorViewSet, basename='training-ambassador')
router.register(r'commissions', CommissionViewSet, basename='training-commission')
router.register(r'assessments', AssessmentViewSet, basename='training-assessment')
router.register(r'certificates', CertificateViewSet, basename='training-certificate')
router.register(r'job-placements', JobPlacementViewSet, basename='training-jobplacement')
router.register(r'class-sessions', ClassSessionViewSet, basename='training-classsession')

urlpatterns = [
    path('', include(router.urls)),
]
