from .base import FirestoreService


class OnboardingService(FirestoreService):
    collection_name = 'hrm_onboarding_tasks'

    @classmethod
    def add_task(cls, data, user):
        cls.create({
            'employee': data.get('employee'),
            'task_name': data.get('task_name'),
            'due_date': data.get('due_date'),
            'status': data.get('status', 'Pending'),
        }, user)

    @classmethod
    def add_exit_clearance(cls, data, user):
        cls.create({
            'employee': data.get('employee'),
            'exit_date': data.get('exit_date'),
            'reason': data.get('reason', ''),
            'it_clearance': data.get('it_clearance', 'Pending'),
            'finance_clearance': data.get('finance_clearance', 'Pending'),
            'hr_clearance': data.get('hr_clearance', 'Pending'),
            'status': data.get('status', 'Pending'),
        }, user)

    @classmethod
    def update_clearance(cls, doc_id, field, value, user):
        from config.firebase import db
        from ..audit import enrich_with_audit
        db.collection('hrm_exit_clearance').document(doc_id).update(
            enrich_with_audit({field: value}, user, is_update=True)
        )
