from .base import ORMService
from ..models import OnboardingTask, ExitClearance, Employee


class OnboardingService(ORMService):
    model = OnboardingTask

    @staticmethod
    def _resolve(doc_id, model_class):
        if not doc_id:
            return None
        try:
            return model_class.objects.get(pk=doc_id)
        except (model_class.DoesNotExist, ValueError):
            pass
        return model_class.objects.filter(pk=doc_id).first()

    @classmethod
    def add_task(cls, data, user):
        emp_name = data.get('employee')
        emp = Employee.objects.filter(name=emp_name).first()
        instance = OnboardingTask.objects.create(
            employee=emp,
            task_name=data.get('task_name'),
            due_date=data.get('due_date') or None,
            status=data.get('status', 'Pending'),
            created_by=user,
            updated_by=user,
        )
    @classmethod
    def add_exit_clearance(cls, data, user):
        emp_name = data.get('employee')
        emp = Employee.objects.filter(name=emp_name).first()
        instance = ExitClearance.objects.create(
            employee=emp,
            exit_date=data.get('exit_date'),
            reason=data.get('reason', ''),
            it_clearance=data.get('it_clearance', 'Pending'),
            finance_clearance=data.get('finance_clearance', 'Pending'),
            hr_clearance=data.get('hr_clearance', 'Pending'),
            status=data.get('status', 'In Progress'),
        )
    @classmethod
    def update_clearance(cls, doc_id, field, value, user):
        instance = cls._resolve(doc_id, ExitClearance)
        if instance:
            setattr(instance, field, value)
            instance.updated_by = user
            instance.save()

    @classmethod
    def update_status(cls, doc_id, status, user):
        instance = cls._resolve(doc_id, OnboardingTask)
        if instance:
            instance.status = status
            instance.updated_by = user
            instance.save(update_fields=['status', 'updated_by'])

    @classmethod
    def delete(cls, doc_id):
        instance = cls._resolve(doc_id, OnboardingTask)
        if instance:
            instance.is_active = False
            instance.save(update_fields=['is_active'])
