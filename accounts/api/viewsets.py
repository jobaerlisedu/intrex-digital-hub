from django.contrib.auth.models import User
from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from accounts.models import AuditLog, ActiveSession
from accounts.api.serializers import UserSerializer, AuditLogSerializer, ActiveSessionSerializer


class IsSuperUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_superuser


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.prefetch_related('groups').all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [IsSuperUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['username', 'email', 'date_joined', 'is_active']

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        user = self.get_object()
        user.is_active = not user.is_active
        user.save()
        return Response({'is_active': user.is_active})


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related('user').all().order_by('-timestamp')
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['action', 'module', 'description', 'user__username']
    ordering_fields = ['timestamp', 'action', 'module']
    ordering = ['-timestamp']


class ActiveSessionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ActiveSession.objects.select_related('user').all().order_by('-last_activity')
    serializer_class = ActiveSessionSerializer
    permission_classes = [IsSuperUser]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['last_activity', 'created_at']
    ordering = ['-last_activity']

    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        session = self.get_object()
        session.delete()
        return Response({'status': 'revoked'})
