from django.db import models
from django.contrib.auth.models import User
from config.tenants import TenantAwareModel
import uuid


class WorkflowDefinition(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    name = models.CharField(max_length=255)
    module = models.CharField(max_length=50, help_text='e.g. hrm, inventory, billing')
    entity_type = models.CharField(max_length=100, help_text='e.g. leave, requisition, invoice')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='wf_def_created')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='wf_def_updated')

    class Meta:
        unique_together = [('module', 'entity_type')]

    def __str__(self):
        return f"{self.module}/{self.entity_type}: {self.name}"


class WorkflowState(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    workflow = models.ForeignKey(
        WorkflowDefinition, on_delete=models.CASCADE,
        related_name='states'
    )
    state_key = models.CharField(max_length=100)
    label = models.CharField(max_length=255)
    is_initial = models.BooleanField(default=False)
    is_final = models.BooleanField(default=False)
    color = models.CharField(max_length=20, default='secondary',
                             help_text='Bootstrap color class')
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        unique_together = [('workflow', 'state_key')]
        ordering = ['workflow', 'order']

    def __str__(self):
        return f"[{self.workflow.module}] {self.label}"


class WorkflowTransition(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    workflow = models.ForeignKey(
        WorkflowDefinition, on_delete=models.CASCADE,
        related_name='transitions'
    )
    from_state = models.ForeignKey(
        WorkflowState, on_delete=models.CASCADE,
        related_name='transitions_from'
    )
    to_state = models.ForeignKey(
        WorkflowState, on_delete=models.CASCADE,
        related_name='transitions_to'
    )
    trigger = models.CharField(max_length=100, help_text='action name, e.g. approve, reject')
    label = models.CharField(max_length=255, blank=True)
    requires_approval = models.BooleanField(default=False)
    allowed_roles = models.JSONField(default=list, blank=True,
                                     help_text='List of group names allowed to trigger')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        unique_together = [('workflow', 'from_state', 'trigger')]

    def __str__(self):
        return f"{self.from_state} → {self.to_state} ({self.trigger})"


class WorkflowInstance(TenantAwareModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    workflow = models.ForeignKey(
        WorkflowDefinition, on_delete=models.CASCADE,
        related_name='instances'
    )
    entity_id = models.CharField(max_length=255, db_index=True,
                                 help_text='Entity key or document ID')
    entity_label = models.CharField(max_length=255, blank=True,
                                    help_text='Human-readable label for the entity')
    current_state = models.ForeignKey(
        WorkflowState, on_delete=models.SET_NULL, null=True,
        related_name='instances'
    )
    context = models.JSONField(default=dict, blank=True,
                               help_text='Arbitrary data attached to the instance')
    is_active = models.BooleanField(default=True)
    started_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    started_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['workflow', 'entity_id']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.workflow.name}#{self.entity_id} [{self.current_state}]"


class WorkflowLog(TenantAwareModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    instance = models.ForeignKey(
        WorkflowInstance, on_delete=models.CASCADE,
        related_name='logs'
    )
    from_state = models.ForeignKey(
        WorkflowState, on_delete=models.SET_NULL, null=True,
        related_name='logs_from'
    )
    to_state = models.ForeignKey(
        WorkflowState, on_delete=models.SET_NULL, null=True,
        related_name='logs_to'
    )
    trigger = models.CharField(max_length=100)
    comment = models.TextField(blank=True)
    performed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    metadata = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.instance} {self.trigger} @ {self.timestamp}"
