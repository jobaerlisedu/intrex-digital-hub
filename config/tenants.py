"""
Multi-tenancy infrastructure.

Usage:
    from config.tenants import TenantAwareModel, TenantManager, TenantQuerySet

    class MyModel(TenantAwareModel):
        name = models.CharField(max_length=255)
        ...
"""
import threading
from django.db import models
from django.db.models import QuerySet, Manager
from django.contrib.auth.models import User

_thread_locals = threading.local()


def get_current_tenant():
    return getattr(_thread_locals, 'tenant_id', None)


def set_current_tenant(tenant_id):
    _thread_locals.tenant_id = tenant_id


def get_current_user():
    return getattr(_thread_locals, 'current_user', None)


def set_current_user(user):
    _thread_locals.current_user = user


class TenantQuerySet(QuerySet):
    def for_tenant(self, tenant_id=None):
        if tenant_id is None:
            tenant_id = get_current_tenant()
        if tenant_id:
            return self.filter(organization_id=tenant_id)
        return self


class TenantManager(Manager):
    def get_queryset(self):
        return TenantQuerySet(self.model, using=self._db)

    def for_tenant(self, tenant_id=None):
        return self.get_queryset().for_tenant(tenant_id)


class TenantAwareModel(models.Model):
    organization = models.ForeignKey(
        'registry.Organization',
        on_delete=models.CASCADE,
        blank=True, null=True,
        related_name='%(app_label)s_%(class)s_set',
    )

    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.organization_id:
            tenant_id = get_current_tenant()
            if tenant_id:
                self.organization_id = tenant_id
        super().save(*args, **kwargs)


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant_id = None
        if request.user.is_authenticated:
            tenant_id = getattr(request.user, 'tenant_id', None)
            set_current_user(request.user)
        set_current_tenant(tenant_id)
        response = self.get_response(request)
        set_current_tenant(None)
        set_current_user(None)
        return response


class TenantViewSetMixin:
    def get_queryset(self):
        qs = super().get_queryset()
        if hasattr(qs, 'for_tenant'):
            return qs.for_tenant()
        return qs

    def perform_create(self, serializer):
        tenant_id = get_current_tenant()
        if tenant_id and 'organization' not in serializer.validated_data:
            serializer.save(organization_id=tenant_id)
        else:
            serializer.save()
