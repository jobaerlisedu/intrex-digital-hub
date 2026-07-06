from django.contrib import admin
from .models import WorkflowDefinition, WorkflowState, WorkflowTransition, WorkflowInstance, WorkflowLog


@admin.register(WorkflowDefinition)
class WorkflowDefinitionAdmin(admin.ModelAdmin):
    list_display = ('name', 'module', 'entity_type', 'is_active')
    list_filter = ('module', 'is_active')
    search_fields = ('name', 'module', 'entity_type')


@admin.register(WorkflowState)
class WorkflowStateAdmin(admin.ModelAdmin):
    list_display = ('state_key', 'label', 'workflow', 'is_initial', 'is_final')
    list_filter = ('is_initial', 'is_final', 'workflow')


@admin.register(WorkflowTransition)
class WorkflowTransitionAdmin(admin.ModelAdmin):
    list_display = ('workflow', 'from_state', 'to_state', 'trigger', 'requires_approval')
    list_filter = ('requires_approval', 'workflow')


@admin.register(WorkflowInstance)
class WorkflowInstanceAdmin(admin.ModelAdmin):
    list_display = ('workflow', 'entity_id', 'current_state', 'is_active', 'started_at')
    list_filter = ('is_active', 'workflow', 'current_state')


@admin.register(WorkflowLog)
class WorkflowLogAdmin(admin.ModelAdmin):
    list_display = ('instance', 'from_state', 'to_state', 'trigger', 'performed_by', 'timestamp')
    list_filter = ('trigger', 'timestamp')
