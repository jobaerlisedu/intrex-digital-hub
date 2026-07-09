from django.contrib.auth.models import User
from config.logger import hrm_logger
from .event_bus import event_bus


def create_notification(recipient, title, message, notification_type='', link='', channel='in_app'):
    from hrm.models import Notification, NotificationPreference

    try:
        prefs, _ = NotificationPreference.objects.get_or_create(user=recipient)
        if channel == 'in_app' and not prefs.notify_in_app:
            return None
        if channel == 'email' and not prefs.notify_email:
            return None

        notification = Notification.objects.create(
            recipient=recipient,
            title=title,
            message=message,
            channel=channel,
            notification_type=notification_type,
            link=link,
        )
        hrm_logger.info(f"Notification created for {recipient.username}: {title}")
        return notification
    except Exception as e:
        hrm_logger.error(f"Failed to create notification: {e}")
        return None


# Map entity types to required group names (without _access suffix)
# Override via NOTIFICATION_ROLE_MAP in Django settings if needed
DEFAULT_ROLE_MAP = {
    'leave': ['hrm_manager', 'hrm_admin'],
    'requisition': ['inventory_manager', 'inventory_admin'],
    'expense_claim': ['hrm_manager', 'finance_admin'],
    'advance_salary': ['hrm_manager', 'finance_admin'],
    'performance_review': ['hrm_manager', 'hrm_admin'],
    'onboarding_task': ['hrm_admin'],
    'exit_clearance': ['hrm_admin'],
}


def _get_target_groups(entity_type):
    from django.conf import settings
    role_map = getattr(settings, 'NOTIFICATION_ROLE_MAP', DEFAULT_ROLE_MAP)
    groups = role_map.get(entity_type, ['admin'])
    return [f'{g}_access' for g in groups]


def notify_workflow_event(event):
    data = event.get('data', {})
    entity_type = data.get('entity_type', '')
    entity_id = data.get('entity_id', '')
    new_status = data.get('new_status', '')
    triggered_by = data.get('triggered_by', '')
    module = data.get('module', '')

    try:
        from registry.services import lookup_person_by_auth_user
        from django.contrib.auth.models import User

        if not triggered_by:
            return
        trigger_user = User.objects.filter(username=triggered_by).first()
        if not trigger_user:
            return

        person = lookup_person_by_auth_user(trigger_user)
        if not person or not person.display_name:
            return

        subject_line = f"{person.display_name} updated {entity_type}"
        detail = f"{entity_type} ({entity_id}) moved to {new_status}"

        group_names = _get_target_groups(entity_type)
        admins = User.objects.filter(
            groups__name__in=group_names,
            is_active=True,
        ).distinct()

        if not admins:
            hrm_logger.warning(
                f"No recipients found for workflow notification: "
                f"entity_type={entity_type}, groups={group_names}"
            )

        for admin in admins:
            if admin == trigger_user:
                continue
            create_notification(
                recipient=admin,
                title=subject_line,
                message=detail,
                notification_type=f'{module}_{entity_type}_status',
                link=f'/{module}/{entity_type}/',
            )
    except Exception as e:
        hrm_logger.error(f"Workflow notification handler error: {e}")


def notify_leave_applied(event):
    data = event.get('data', {})
    emp_name = data.get('employee_name', '')
    leave_type = data.get('leave_type', '')
    duration = data.get('duration', '')
    doc_id = data.get('doc_id', '')

    try:
        managers = User.objects.filter(
            groups__name='hrm_access', is_active=True
        ).exclude(username=data.get('applied_by', ''))

        for mgr in managers:
            create_notification(
                recipient=mgr,
                title=f"Leave Request: {emp_name}",
                message=f"{emp_name} applied for {leave_type} ({duration})",
                notification_type='leave_applied',
                link='/hrm/leave/',
            )
    except Exception as e:
        hrm_logger.error(f"Leave notification error: {e}")


def notify_performance_review(event):
    data = event.get('data', {})
    emp_name = data.get('employee_name', '')
    reviewer_name = data.get('reviewer_name', '')
    review_id = data.get('review_id', '')
    cycle_name = data.get('cycle_name', '')

    try:
        from django.contrib.auth.models import User
        from registry.services import lookup_person_by_auth_user

        if reviewer_name:
            reviewer_users = User.objects.filter(
                groups__name='hrm_access', is_active=True
            )
            for u in reviewer_users:
                p = lookup_person_by_auth_user(u)
                if p and p.display_name == reviewer_name:
                    create_notification(
                        recipient=u,
                        title=f"Review Assigned: {emp_name}",
                        message=f"You've been assigned as reviewer for {emp_name} ({cycle_name})",
                        notification_type='review_assigned',
                        link='/hrm/performance/',
                    )
                    break
    except Exception as e:
        hrm_logger.error(f"Performance review notification error: {e}")


def init_event_subscribers():
    event_bus.subscribe('workflow.transition', notify_workflow_event)
    event_bus.subscribe('leave.applied', notify_leave_applied)
    event_bus.subscribe('performance.review_assigned', notify_performance_review)
    hrm_logger.info("Notification event subscribers initialized")
