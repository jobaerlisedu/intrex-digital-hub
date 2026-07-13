from .base import ORMService
from ..models import Attendance, Employee


class AttendanceService(ORMService):
    model = Attendance

    @classmethod
    def _resolve(cls, doc_id):
        if not doc_id:
            return None
        try:
            return cls.model.objects.get(pk=doc_id)
        except (cls.model.DoesNotExist, ValueError):
            pass
        return cls.model.objects.filter(pk=doc_id).first()

    @classmethod
    def record_attendance(cls, data, user):
        emp_name = data.get('name')
        emp = Employee.objects.filter(name=emp_name).first()
        att_data = {
            'employee': emp,
            'date': data.get('date'),
            'check_in': data.get('check_in', None),
            'check_out': data.get('check_out', None),
            'status': data.get('status', 'Present'),
        }
        if user:
            att_data['created_by'] = user
            att_data['updated_by'] = user
        instance = Attendance.objects.create(**att_data)
    @classmethod
    def resolve_missing(cls, data, user):
        emp_name = data.get('missing_name')
        emp = Employee.objects.filter(name=emp_name).first()
        att_data = {
            'employee': emp,
            'date': data.get('missing_date'),
            'status': data.get('corrected_status', 'Present'),
            'resolved': True,
        }
        if user:
            att_data['created_by'] = user
            att_data['updated_by'] = user
        instance = Attendance.objects.create(**att_data)
    @classmethod
    def get_attendance_context(cls):
        logs = list(Attendance.objects.filter(is_active=True).select_related('employee').order_by('-date').values(
            'pk', 'employee__name', 'date', 'check_in', 'check_out', 'status', 'resolved',
        ))
        for l in logs:
            l['id'] = l.pop('pk') or ''
            l['name'] = l.pop('employee__name', '')
            l['date'] = str(l['date']) if l['date'] else ''

        try:
            employees = [{'name': e.name} for e in Employee.objects.filter(is_active=True) if e.name]
        except Exception:
            employees = []

        missing_logs = [l for l in logs if l.get('status') == 'Absent']
        return logs, employees, missing_logs

    @classmethod
    def delete(cls, doc_id):
        instance = cls._resolve(doc_id)
        if instance:
            instance.is_active = False
            instance.save(update_fields=['is_active'])
