from .base import ORMService
from ..models import ExpenseClaim, Employee


class ExpenseService(ORMService):
    model = ExpenseClaim

    @staticmethod
    def _resolve(doc_id):
        if not doc_id:
            return None
        try:
            return ExpenseClaim.objects.get(pk=doc_id)
        except (ExpenseClaim.DoesNotExist, ValueError):
            pass
        return ExpenseClaim.objects.filter(pk=doc_id).first()

    @classmethod
    def file_claim(cls, data, user):
        emp_name = data.get('employee')
        emp = Employee.objects.filter(name=emp_name).first()
        instance = ExpenseClaim.objects.create(
            employee=emp,
            category=data.get('category'),
            amount=float(data.get('amount', 0)),
            description=data.get('description', ''),
            status='Pending',
            created_by=user,
            updated_by=user,
        )
    @classmethod
    def approve_claim(cls, doc_id, user):
        instance = cls._resolve(doc_id)
        if instance:
            instance.status = 'Approved'
            instance.updated_by = user
            instance.save(update_fields=['status', 'updated_by'])

    @classmethod
    def reject_claim(cls, doc_id, user):
        instance = cls._resolve(doc_id)
        if instance:
            instance.status = 'Rejected'
            instance.updated_by = user
            instance.save(update_fields=['status', 'updated_by'])

    @classmethod
    def delete(cls, doc_id):
        instance = cls._resolve(doc_id)
        if instance:
            instance.is_active = False
            instance.save(update_fields=['is_active'])
