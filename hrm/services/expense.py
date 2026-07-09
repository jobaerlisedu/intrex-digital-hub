from .base import FirestoreService


class ExpenseService(FirestoreService):
    collection_name = 'hrm_expense_claims'

    @classmethod
    def file_claim(cls, data, user):
        cls.create({
            'employee': data.get('employee'),
            'category': data.get('category'),
            'amount': float(data.get('amount', 0)),
            'description': data.get('description', ''),
            'status': 'Pending',
        }, user)

    @classmethod
    def approve_claim(cls, doc_id, user):
        cls.update_status(doc_id, 'Approved', user)

    @classmethod
    def reject_claim(cls, doc_id, user):
        cls.update_status(doc_id, 'Rejected', user)
