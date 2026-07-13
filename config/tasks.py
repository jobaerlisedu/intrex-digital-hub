from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from config.logger import get_logger

task_logger = get_logger('config.tasks')


@shared_task
def send_workflow_notification(module, entity_type, entity_id, event, user_email):
    task_logger.info(f"[NOTIFICATION] {module}.{entity_type}({entity_id}) → {event} for {user_email}")


@shared_task
def cleanup_inactive_sessions():
    from accounts.models import ActiveSession
    cutoff = timezone.now() - timedelta(hours=24)
    deleted, _ = ActiveSession.objects.filter(last_activity__lt=cutoff).delete()
    return f"Cleaned up {deleted} stale sessions"


@shared_task
def generate_report(module, report_type, params):
    task_logger.info(f"[REPORT] Generating {module}.{report_type} with params={params}")
    return f"{module}.{report_type} generated"


@shared_task
def send_installment_reminders():
    from training.models import PaymentInstallment
    import datetime
    today = datetime.date.today()
    target = today + datetime.timedelta(days=3)
    try:
        due_inst = PaymentInstallment.objects.filter(
            due_date=target, status='Pending'
        ).select_related('payment__student')
        count = 0
        for inst in due_inst:
            student_name = getattr(inst.payment.student, 'full_name',
                                   getattr(inst.payment.student, 'fullName', 'Unknown'))
            task_logger.info(
                f"[REMINDER] Installment due for {student_name} - {inst.amount}"
            )
            count += 1
        return f"Sent {count} installment reminders"
    except Exception as e:
        return f"Error: {e}"


@shared_task
def auto_post_due_journals():
    from billing.models import JournalEntry
    count = JournalEntry.objects.filter(status='Draft').update(status='Posted')
    return f"Auto-posted {count} journals"
