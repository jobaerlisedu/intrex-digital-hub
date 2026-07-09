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


def _employee_to_user(emp):
    """Get the auth User linked to an Employee via registry.Person."""
    try:
        from registry.models import Person
        if not emp.firestore_id:
            return None
        person = Person.objects.filter(firestore_employee_id=emp.firestore_id).first()
        if person and person.auth_user:
            return person.auth_user
    except Exception:
        pass
    return None


def notify_manager_or_group(emp_name, detail, notification_type, link, event_data, applied_by):
    try:
        from hrm.models import Employee

        email = event_data.get('employee_email', '')
        manager_user = None
        if email:
            emp = Employee.objects.filter(email=email, is_active=True).first()
            if emp and emp.reporting_to:
                manager_user = _employee_to_user(emp.reporting_to)

        if manager_user and manager_user.is_active:
            create_notification(
                recipient=manager_user,
                title=f"{notification_type}: {emp_name}",
                message=detail,
                notification_type=notification_type,
                link=link,
            )
            return
    except Exception as e:
        hrm_logger.error(f"Manager lookup error: {e}")

    # Fallback: notify all hrm_access users
    try:
        fallback = User.objects.filter(
            groups__name='hrm_access', is_active=True
        ).exclude(username=applied_by)
        for u in fallback:
            create_notification(
                recipient=u,
                title=f"{notification_type}: {emp_name}",
                message=detail,
                notification_type=notification_type,
                link=link,
            )
    except Exception as e:
        hrm_logger.error(f"Fallback notification error: {e}")


def notify_leave_applied(event):
    data = event.get('data', {})
    emp_name = data.get('employee_name', '')
    leave_type = data.get('leave_type', '')
    duration = data.get('duration', '')
    detail = f"{emp_name} applied for {leave_type} ({duration})"
    notify_manager_or_group(emp_name, detail, 'leave_applied', '/hrm/leave/', data, data.get('applied_by', ''))


def notify_advance_salary_applied(event):
    data = event.get('data', {})
    emp_name = data.get('employee_name', '')
    amount = data.get('amount', '')
    deduct_month = data.get('deduct_month', '')
    detail = f"{emp_name} requested advance of {amount} (deduct {deduct_month})"
    notify_manager_or_group(emp_name, detail, 'advance_salary_applied', '/hrm/payroll/', data, data.get('applied_by', ''))


def notify_leave_decided(event, approved=True):
    data = event.get('data', {})
    emp_name = data.get('employee_name', '')
    leave_type = data.get('leave_type', '')
    duration = data.get('duration', '')
    actor = data.get('approved_by') or data.get('rejected_by', '')
    status = 'approved' if approved else 'rejected'
    reason = data.get('rejection_reason', '') if not approved else ''

    try:
        emp_users = User.objects.filter(
            username__iexact=data.get('employee_email', '').split('@')[0],
            is_active=True,
        )
        for u in emp_users:
            msg = f"Your {leave_type} request ({duration}) was {status} by {actor}."
            if reason:
                msg += f" Reason: {reason}"
            create_notification(
                recipient=u,
                title=f"Leave {status}: {emp_name}",
                message=msg,
                notification_type=f'leave_{status}',
                link='/hrm/leave/',
            )
    except Exception as e:
        hrm_logger.error(f"Leave {status} notification error: {e}")


def notify_leave_approved(event):
    notify_leave_decided(event, approved=True)


def notify_leave_rejected(event):
    notify_leave_decided(event, approved=False)


def notify_advance_salary_decided(event, approved=True):
    data = event.get('data', {})
    emp_name = data.get('employee_name', '')
    amount = data.get('amount', '')
    actor = data.get('approved_by') or data.get('rejected_by', '')
    status = 'approved' if approved else 'rejected'
    reason = data.get('rejection_reason', '') if not approved else ''

    try:
        emp_users = User.objects.filter(
            username__iexact=data.get('employee_email', '').split('@')[0],
            is_active=True,
        )
        for u in emp_users:
            msg = f"Your advance salary request ({amount}) was {status} by {actor}."
            if reason:
                msg += f" Reason: {reason}"
            create_notification(
                recipient=u,
                title=f"Advance Salary {status}: {emp_name}",
                message=msg,
                notification_type=f'advance_salary_{status}',
                link='/hrm/payroll/',
            )
    except Exception as e:
        hrm_logger.error(f"Advance salary {status} notification error: {e}")


def notify_advance_salary_approved(event):
    notify_advance_salary_decided(event, approved=True)


def notify_advance_salary_rejected(event):
    notify_advance_salary_decided(event, approved=False)


def notify_expense_claim_decided(event, approved=True):
    data = event.get('data', {})
    emp_name = data.get('employee_name', '')
    amount = data.get('amount', '')
    category = data.get('category', '')
    actor = data.get('approved_by') or data.get('rejected_by', '')
    status = 'approved' if approved else 'rejected'
    reason = data.get('rejection_reason', '') if not approved else ''

    try:
        emp_users = User.objects.filter(
            username__iexact=data.get('employee_email', '').split('@')[0],
            is_active=True,
        )
        for u in emp_users:
            msg = f"Your {category} expense claim ({amount}) was {status} by {actor}."
            if reason:
                msg += f" Reason: {reason}"
            create_notification(
                recipient=u,
                title=f"Expense Claim {status}: {emp_name}",
                message=msg,
                notification_type=f'expense_claim_{status}',
                link='/hrm/expenses/',
            )
    except Exception as e:
        hrm_logger.error(f"Expense claim {status} notification error: {e}")


def notify_expense_claim_approved(event):
    notify_expense_claim_decided(event, approved=True)


def notify_expense_claim_rejected(event):
    notify_expense_claim_decided(event, approved=False)


def init_event_subscribers():
    event_bus.subscribe('leave.applied', notify_leave_applied)
    event_bus.subscribe('leave.approved', notify_leave_approved)
    event_bus.subscribe('leave.rejected', notify_leave_rejected)
    event_bus.subscribe('advance_salary.applied', notify_advance_salary_applied)
    event_bus.subscribe('advance_salary.approved', notify_advance_salary_approved)
    event_bus.subscribe('advance_salary.rejected', notify_advance_salary_rejected)
    event_bus.subscribe('expense_claim.approved', notify_expense_claim_approved)
    event_bus.subscribe('expense_claim.rejected', notify_expense_claim_rejected)
    hrm_logger.info("Notification event subscribers initialized")
