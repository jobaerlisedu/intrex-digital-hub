"""
Workflow integration helpers for views.
Maps model status strings to workflow triggers.
"""
from workflow.services import start_workflow, transition, get_instance


WORKFLOW_MAP = {
    'hrm': {'leave': 'leave'},
    'inventory': {
        'requisition': 'requisition',
        'purchase_order': 'purchase_order',
    },
    'billing': {'invoice': 'invoice'},
    'solutions': {'project': 'project'},
}


def ensure_workflow(module, entity_type, entity_id, entity_label='', request=None):
    instance = get_instance(module, entity_type, entity_id)
    if instance is None:
        instance = start_workflow(
            module, entity_type, entity_id,
            entity_label=entity_label,
            context={},
            user=request.user if request and request.user.is_authenticated else None,
        )
    return instance


def try_transition(module, entity_type, entity_id, trigger, request=None, comment=''):
    instance = get_instance(module, entity_type, entity_id)
    if instance is None:
        return False, 'No active workflow instance found'
    success, error = transition(
        instance, trigger,
        user=request.user if request and request.user.is_authenticated else None,
        comment=comment,
    )
    return success, error


# Status-to-trigger mappings
LEAVE_TRIGGER_MAP = {
    'Approved': 'approve',
    'Rejected': 'reject',
}

REQUISITION_TRIGGER_MAP = {
    'Approved': 'approve',
    'Rejected': 'reject',
    'Procuring': 'start_procurement',
    'Dispatched': 'dispatch',
    'Completed': 'complete',
    'Partially Received': 'partial_receipt',
}

INVOICE_TRIGGER_MAP = {
    'Paid': 'pay_full',
    'Partially Paid': 'pay_partial',
    'Overdue': 'mark_overdue',
}

PROJECT_TRIGGER_MAP = {
    'In Progress': 'start',
    'Completed': 'complete',
    'Cancelled': 'cancel',
}

PO_TRIGGER_MAP = {
    'Approved': 'approve',
    'Cancelled': 'cancel',
    'Fulfilled': 'receive_full',
    'Partially Received': 'receive_partial',
}
