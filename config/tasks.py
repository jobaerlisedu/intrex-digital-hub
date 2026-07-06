from celery import shared_task
from django.utils import timezone
from datetime import timedelta


@shared_task
def send_workflow_notification(module, entity_type, entity_id, event, user_email):
    print(f"[NOTIFICATION] {module}.{entity_type}({entity_id}) → {event} for {user_email}")


@shared_task
def cleanup_inactive_sessions():
    from accounts.models import ActiveSession
    cutoff = timezone.now() - timedelta(hours=24)
    deleted, _ = ActiveSession.objects.filter(last_activity__lt=cutoff).delete()
    return f"Cleaned up {deleted} stale sessions"


@shared_task
def generate_report(module, report_type, params):
    print(f"[REPORT] Generating {module}.{report_type} with params={params}")
    return f"{module}.{report_type} generated"


@shared_task
def send_installment_reminders():
    from config.firebase import db
    import datetime
    today = datetime.date.today()
    target = today + datetime.timedelta(days=3)
    target_str = target.strftime('%Y-%m-%d')
    from google.cloud.firestore import FILTER
    try:
        regs = db.collection('trn_registrations').stream()
        count = 0
        for reg in regs:
            data = reg.to_dict()
            payments_doc = db.collection('trn_payments').document(reg.id).get()
            if payments_doc.exists:
                pay_data = payments_doc.to_dict()
                installments = pay_data.get('installments', [])
                for inst in installments:
                    if inst.get('due_date') == target_str and not inst.get('paid', False):
                        print(f"[REMINDER] Installment due for {data.get('fullName')} - {inst.get('amount')}")
                        count += 1
        return f"Sent {count} installment reminders"
    except Exception as e:
        return f"Error: {e}"


@shared_task
def auto_post_due_journals():
    from config.firebase import db
    journals = db.collection('fin_journal_entries').where('status', '==', 'Draft').stream()
    count = 0
    for j in journals:
        db.collection('fin_journal_entries').document(j.id).update({'status': 'Posted'})
        count += 1
    return f"Auto-posted {count} journals"


@shared_task
def sync_user_to_firestore(user_id):
    from django.contrib.auth.models import User
    from config.firebase import db
    try:
        user = User.objects.get(id=user_id)
        db.collection('sys_users').document(str(user.id)).set({
            'email': user.email,
            'username': user.username,
            'is_active': user.is_active,
            'last_login': str(user.last_login) if user.last_login else None,
            'updated_at': timezone.now().isoformat(),
        })
        return f"Synced user {user_id}"
    except User.DoesNotExist:
        return f"User {user_id} not found"
