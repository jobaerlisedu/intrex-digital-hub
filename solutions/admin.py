from django.contrib import admin
from . import models


class ProjectPhaseInline(admin.TabularInline):
    model = models.ProjectPhase
    extra = 0
    fields = ['phase_name', 'budget_allocation', 'status', 'start_date', 'end_date']


class ProjectStakeholderInline(admin.TabularInline):
    model = models.ProjectStakeholder
    extra = 0


@admin.register(models.Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['project_code', 'name', 'client_name', 'total_budget', 'status', 'start_date', 'end_date']
    list_filter = ['status', 'category']
    search_fields = ['project_code', 'name', 'client_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [ProjectPhaseInline, ProjectStakeholderInline]


@admin.register(models.ProjectPhase)
class ProjectPhaseAdmin(admin.ModelAdmin):
    list_display = ['project', 'phase_name', 'budget_allocation', 'status', 'start_date', 'end_date']
    list_filter = ['status']
    search_fields = ['project__name', 'phase_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['project']


class TaskInline(admin.TabularInline):
    model = models.Task
    extra = 0
    fields = ['task_name', 'assigned_to', 'priority', 'status', 'due_date']


@admin.register(models.Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['task_name', 'phase', 'assigned_to', 'priority', 'status', 'due_date']
    list_filter = ['status', 'priority']
    search_fields = ['task_name', 'assigned_to']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['phase']


@admin.register(models.ProjectRequisition)
class ProjectRequisitionAdmin(admin.ModelAdmin):
    list_display = ['project', 'item_name', 'quantity', 'estimated_cost', 'status']
    list_filter = ['status']
    search_fields = ['project__name', 'item_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['project', 'phase']


@admin.register(models.SoftwareLicense)
class SoftwareLicenseAdmin(admin.ModelAdmin):
    list_display = ['license_name', 'project', 'subscription_tier', 'renewal_date', 'cost', 'status']
    list_filter = ['status', 'subscription_tier']
    search_fields = ['license_name', 'project__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['project']


@admin.register(models.ProjectStakeholder)
class ProjectStakeholderAdmin(admin.ModelAdmin):
    list_display = ['contact_name', 'project', 'role', 'email', 'phone']
    list_filter = ['role']
    search_fields = ['contact_name', 'email', 'project__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['project']


@admin.register(models.Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ['title', 'project', 'meeting_date', 'start_time']
    list_filter = ['meeting_date']
    search_fields = ['title', 'project__name', 'agenda']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['project']
