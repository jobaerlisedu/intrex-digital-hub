from django.contrib.auth.models import User
from .models import (
    WorkflowDefinition, WorkflowState, WorkflowTransition,
    WorkflowInstance, WorkflowLog
)


def get_or_create_workflow(module, entity_type, name, description=''):
    wf, created = WorkflowDefinition.objects.get_or_create(
        module=module,
        entity_type=entity_type,
        defaults={
            'name': name,
            'description': description,
        }
    )
    return wf, created


def add_state(workflow, state_key, label, is_initial=False, is_final=False,
              color='secondary', order=0):
    state, created = WorkflowState.objects.get_or_create(
        workflow=workflow,
        state_key=state_key,
        defaults={
            'label': label,
            'is_initial': is_initial,
            'is_final': is_final,
            'color': color,
            'order': order,
        }
    )
    return state, created


def add_transition(workflow, from_state_key, to_state_key, trigger,
                   label='', requires_approval=False, allowed_roles=None):
    from_state = WorkflowState.objects.get(workflow=workflow, state_key=from_state_key)
    to_state = WorkflowState.objects.get(workflow=workflow, state_key=to_state_key)
    trans, created = WorkflowTransition.objects.get_or_create(
        workflow=workflow,
        from_state=from_state,
        trigger=trigger,
        defaults={
            'to_state': to_state,
            'label': label or f"{from_state.label} → {to_state.label}",
            'requires_approval': requires_approval,
            'allowed_roles': allowed_roles or [],
        }
    )
    return trans, created


def start_workflow(module, entity_type, entity_id, entity_label='',
                   context=None, user=None):
    try:
        wf = WorkflowDefinition.objects.get(module=module, entity_type=entity_type, is_active=True)
    except WorkflowDefinition.DoesNotExist:
        return None

    initial_state = wf.states.filter(is_initial=True).first()
    if not initial_state:
        return None

    instance, created = WorkflowInstance.objects.get_or_create(
        workflow=wf,
        entity_id=entity_id,
        defaults={
            'entity_label': entity_label or entity_id,
            'current_state': initial_state,
            'context': context or {},
            'started_by': user,
        }
    )
    if created:
        WorkflowLog.objects.create(
            instance=instance,
            from_state=None,
            to_state=initial_state,
            trigger='__start__',
            comment='Workflow started',
            performed_by=user,
        )
    return instance


def transition(instance, trigger, user=None, comment='', metadata=None):
    current_state = instance.current_state
    try:
        transition_def = WorkflowTransition.objects.get(
            workflow=instance.workflow,
            from_state=current_state,
            trigger=trigger,
        )
    except WorkflowTransition.DoesNotExist:
        return False, f"Transition '{trigger}' not allowed from state '{current_state}'"

    if transition_def.allowed_roles and user:
        user_roles = set(user.groups.values_list('name', flat=True))
        if not user_roles.intersection(transition_def.allowed_roles):
            return False, f"User not authorized for '{trigger}' transition"

    old_state = instance.current_state
    instance.current_state = transition_def.to_state
    if transition_def.to_state.is_final:
        instance.is_active = False
        from django.utils import timezone
        instance.completed_at = timezone.now()
    instance.save()

    WorkflowLog.objects.create(
        instance=instance,
        from_state=old_state,
        to_state=transition_def.to_state,
        trigger=trigger,
        comment=comment,
        performed_by=user,
        metadata=metadata or {},
    )
    return True, None


def get_instance(module, entity_type, entity_id):
    try:
        wf = WorkflowDefinition.objects.get(module=module, entity_type=entity_type)
        return WorkflowInstance.objects.get(workflow=wf, entity_id=entity_id, is_active=True)
    except (WorkflowDefinition.DoesNotExist, WorkflowInstance.DoesNotExist):
        return None


def get_available_transitions(instance, user=None):
    if not instance or not instance.is_active:
        return []
    current_state = instance.current_state
    transitions = WorkflowTransition.objects.filter(
        workflow=instance.workflow,
        from_state=current_state,
    )
    result = []
    for t in transitions:
        if t.allowed_roles and user:
            user_roles = set(user.groups.values_list('name', flat=True))
            if not user_roles.intersection(t.allowed_roles):
                continue
        result.append({
            'trigger': t.trigger,
            'label': t.label or t.trigger,
            'to_state': t.to_state.state_key,
            'to_state_label': t.to_state.label,
            'requires_approval': t.requires_approval,
        })
    return result


def get_status_display(module, entity_type, state_key):
    try:
        wf = WorkflowDefinition.objects.get(module=module, entity_type=entity_type)
        state = WorkflowState.objects.get(workflow=wf, state_key=state_key)
        return state.label, state.color
    except (WorkflowDefinition.DoesNotExist, WorkflowState.DoesNotExist):
        return state_key, 'secondary'


def initialize_standard_workflows():
    _init_leave_workflow()
    _init_requisition_workflow()
    _init_invoice_workflow()
    _init_project_workflow()
    _init_purchase_order_workflow()


def _init_leave_workflow():
    wf, _ = get_or_create_workflow('hrm', 'leave', 'Leave Approval')
    add_state(wf, 'pending', 'Pending', is_initial=True, color='warning', order=10)
    add_state(wf, 'approved', 'Approved', color='success', order=20)
    add_state(wf, 'rejected', 'Rejected', is_final=True, color='danger', order=30)
    add_transition(wf, 'pending', 'approved', 'approve', 'Approve')
    add_transition(wf, 'pending', 'rejected', 'reject', 'Reject')


def _init_requisition_workflow():
    wf, _ = get_or_create_workflow('inventory', 'requisition', 'Requisition Fulfillment')
    add_state(wf, 'pending_approval', 'Pending Approval', is_initial=True, color='warning', order=10)
    add_state(wf, 'approved', 'Approved', color='info', order=20)
    add_state(wf, 'procuring', 'Procuring', color='primary', order=30)
    add_state(wf, 'dispatched', 'Dispatched', color='secondary', order=40)
    add_state(wf, 'completed', 'Completed', is_final=True, color='success', order=50)
    add_state(wf, 'rejected', 'Rejected', is_final=True, color='danger', order=60)
    add_state(wf, 'partially_received', 'Partially Received', color='warning', order=45)
    add_transition(wf, 'pending_approval', 'approved', 'approve', 'Approve')
    add_transition(wf, 'pending_approval', 'rejected', 'reject', 'Reject')
    add_transition(wf, 'approved', 'procuring', 'start_procurement', 'Start Procurement')
    add_transition(wf, 'procuring', 'dispatched', 'dispatch', 'Dispatch')
    add_transition(wf, 'dispatched', 'completed', 'complete', 'Complete Delivery')
    add_transition(wf, 'dispatched', 'partially_received', 'partial_receipt', 'Partial Receipt')
    add_transition(wf, 'partially_received', 'completed', 'complete', 'Complete Delivery')


def _init_invoice_workflow():
    wf, _ = get_or_create_workflow('billing', 'invoice', 'Invoice Lifecycle')
    add_state(wf, 'pending', 'Pending', is_initial=True, color='warning', order=10)
    add_state(wf, 'partially_paid', 'Partially Paid', color='info', order=20)
    add_state(wf, 'paid', 'Paid', is_final=True, color='success', order=30)
    add_state(wf, 'overdue', 'Overdue', color='danger', order=15)
    add_transition(wf, 'pending', 'paid', 'pay_full', 'Pay in Full')
    add_transition(wf, 'pending', 'partially_paid', 'pay_partial', 'Partial Payment')
    add_transition(wf, 'pending', 'overdue', 'mark_overdue', 'Mark Overdue')
    add_transition(wf, 'partially_paid', 'paid', 'pay_full', 'Pay Remaining')
    add_transition(wf, 'overdue', 'paid', 'pay_full', 'Pay in Full')
    add_transition(wf, 'overdue', 'partially_paid', 'pay_partial', 'Partial Payment')


def _init_project_workflow():
    wf, _ = get_or_create_workflow('solutions', 'project', 'Project Lifecycle')
    add_state(wf, 'not_started', 'Not Started', is_initial=True, color='secondary', order=10)
    add_state(wf, 'in_progress', 'In Progress', color='primary', order=20)
    add_state(wf, 'completed', 'Completed', is_final=True, color='success', order=30)
    add_state(wf, 'cancelled', 'Cancelled', is_final=True, color='danger', order=40)
    add_transition(wf, 'not_started', 'in_progress', 'start', 'Start Project')
    add_transition(wf, 'in_progress', 'completed', 'complete', 'Complete Project')
    add_transition(wf, 'not_started', 'cancelled', 'cancel', 'Cancel Project')
    add_transition(wf, 'in_progress', 'cancelled', 'cancel', 'Cancel Project')


def _init_purchase_order_workflow():
    wf, _ = get_or_create_workflow('inventory', 'purchase_order', 'Purchase Order Lifecycle')
    add_state(wf, 'draft', 'Draft', is_initial=True, color='secondary', order=10)
    add_state(wf, 'approved', 'Approved', color='info', order=20)
    add_state(wf, 'fulfilled', 'Fulfilled', is_final=True, color='success', order=30)
    add_state(wf, 'cancelled', 'Cancelled', is_final=True, color='danger', order=40)
    add_state(wf, 'partially_received', 'Partially Received', color='warning', order=25)
    add_transition(wf, 'draft', 'approved', 'approve', 'Approve')
    add_transition(wf, 'draft', 'cancelled', 'cancel', 'Cancel')
    add_transition(wf, 'approved', 'fulfilled', 'receive_full', 'Receive Full')
    add_transition(wf, 'approved', 'partially_received', 'receive_partial', 'Receive Partial')
    add_transition(wf, 'partially_received', 'fulfilled', 'receive_full', 'Receive Full')
