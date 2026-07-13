from .base import ORMService
from ..models import EmployeeShift, Employee


class RosterService(ORMService):
    model = EmployeeShift

    @staticmethod
    def _resolve(doc_id):
        if not doc_id:
            return None
        try:
            return EmployeeShift.objects.get(pk=doc_id)
        except (EmployeeShift.DoesNotExist, ValueError):
            pass
        return EmployeeShift.objects.filter(pk=doc_id).first()

    @classmethod
    def assign_shift(cls, data, user):
        emp_name = data.get('employee')
        emp = Employee.objects.filter(name=emp_name).first()
        instance = EmployeeShift.objects.create(
            employee=emp,
            shift_name=data.get('shift_name'),
            start_date=data.get('start_date'),
            end_date=data.get('end_date') or None,
        )
    @classmethod
    def delete(cls, doc_id):
        instance = cls._resolve(doc_id)
        if instance:
            instance.is_active = False
            instance.save(update_fields=['is_active'])
