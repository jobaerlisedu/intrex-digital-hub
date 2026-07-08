from django.urls import path, include
from rest_framework.routers import DefaultRouter
from accounts.api.viewsets import UserViewSet, AuditLogViewSet, ActiveSessionViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'audit-logs', AuditLogViewSet)
router.register(r'sessions', ActiveSessionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
