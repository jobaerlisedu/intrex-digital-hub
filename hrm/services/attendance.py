from config.firebase import db
from config.logger import hrm_logger
from ..audit import enrich_with_audit
from ..validators import validate_attendance_data
from ..views_helpers import get_collection_data
from .base import FirestoreService


class AttendanceService(FirestoreService):
    collection_name = 'hrm_attendance'

    @classmethod
    def record_attendance(cls, data, user):
        att_data = {
            'name': data.get('name'),
            'date': data.get('date'),
            'check_in': data.get('check_in', ''),
            'check_out': data.get('check_out', ''),
            'status': data.get('status', 'Present'),
        }
        cls.create(att_data, user)

    @classmethod
    def resolve_missing(cls, data, user):
        att_data = {
            'name': data.get('missing_name'),
            'date': data.get('missing_date'),
            'status': data.get('corrected_status', 'Present'),
            'check_in': '',
            'check_out': '',
            'resolved': True,
        }
        cls.create(att_data, user)

    @classmethod
    def get_attendance_context(cls):
        logs = get_collection_data('hrm_attendance', [])
        try:
            emp_docs = db.collection('hrm_employees').stream()
            employees = [{'name': d.to_dict().get('name', '')} for d in emp_docs if d.to_dict().get('name')]
        except Exception:
            employees = []
        missing_logs = [l for l in logs if l.get('status') == 'Absent']
        return logs, employees, missing_logs
