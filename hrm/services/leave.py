from config.firebase import db
from config.logger import hrm_logger
from ..audit import enrich_with_audit
from ..validators import validate_leave_data, validate_holiday_data
from ..views_helpers import get_collection_data
from .base import FirestoreService
from config.workflow_integration import ensure_workflow, try_transition, LEAVE_TRIGGER_MAP


class LeaveService(FirestoreService):
    collection_name = 'hrm_leaves'

    @classmethod
    def add_holiday(cls, data, user):
        doc_id = data.get('doc_id')
        base_data = {
            'holiday_name': data.get('holiday_name'),
            'from_date': data.get('from_date'),
            'to_date': data.get('to_date'),
            'type': data.get('holiday_type', 'Public'),
        }
        if doc_id:
            db.collection('hrm_holidays').document(doc_id).update(
                enrich_with_audit(base_data, user, is_update=True)
            )
            return 'updated'
        else:
            db.collection('hrm_holidays').add(
                enrich_with_audit(base_data, user, is_update=False)
            )
            return 'created'

    @classmethod
    def delete_holiday(cls, doc_id):
        db.collection('hrm_holidays').document(doc_id).delete()

    @classmethod
    def apply_leave(cls, data, user):
        doc_id = data.get('doc_id')
        from_date = data.get('from_date', '')
        to_date = data.get('to_date', '')
        try:
            from datetime import date as dt
            fd = dt.fromisoformat(from_date)
            td = dt.fromisoformat(to_date)
            days = (td - fd).days + 1
            duration = f"{days} Day{'s' if days != 1 else ''}"
        except Exception:
            duration = data.get('duration', '')

        base_data = {
            'name': data.get('emp_name'),
            'type': data.get('leave_type'),
            'from_date': from_date,
            'to_date': to_date,
            'duration': duration,
            'reason': data.get('reason', ''),
            'status': 'Pending',
        }

        if doc_id:
            cls.update(doc_id, base_data, user)
            emp_name = data.get('emp_name', '')
            ensure_workflow('hrm', 'leave', doc_id, entity_label=emp_name)
            return 'updated'
        else:
            new_id = cls.create(base_data, user)
            emp_name = data.get('emp_name', '')
            ensure_workflow('hrm', 'leave', doc_id or new_id, entity_label=emp_name)
            return 'created'

    @classmethod
    def approve_or_reject(cls, doc_id, status, user):
        db.collection('hrm_leaves').document(doc_id).update(
            enrich_with_audit({'status': status}, user, is_update=True)
        )
        ensure_workflow('hrm', 'leave', doc_id)
        trigger = LEAVE_TRIGGER_MAP.get(status)
        if trigger:
            try_transition('hrm', 'leave', doc_id, trigger)

    @classmethod
    def save_weekend(cls, weekend_days):
        db.collection('hrm_settings').document('weekend').set({'days': weekend_days})

    @classmethod
    def get_leave_context(cls):
        holidays = get_collection_data('hrm_holidays', [])
        leaves = get_collection_data('hrm_leaves', [])

        try:
            emp_docs = db.collection('hrm_employees').stream()
            employees = [{'name': d.to_dict().get('name', '')} for d in emp_docs if d.to_dict().get('name')]
        except Exception:
            employees = []

        try:
            ws_doc = db.collection('hrm_settings').document('weekend').get()
            weekend_days = ws_doc.to_dict().get('days', ['Saturday', 'Sunday']) if ws_doc.exists else ['Saturday', 'Sunday']
        except Exception:
            weekend_days = ['Saturday', 'Sunday']

        try:
            emp_balances = []
            for emp in employees:
                balances = list(db.collection('hrm_leave_balances')
                              .where('employee', '==', f'hrm_employees/{emp.get("id")}')
                              .where('is_active', '==', True)
                              .stream())
                emp_balances.append({
                    'name': emp['name'],
                    'balances': [
                        {
                            'leave_type': b.to_dict().get('leave_type', ''),
                            'entitled': b.to_dict().get('entitled', 0),
                            'used': b.to_dict().get('used', 0),
                            'pending': b.to_dict().get('pending', 0),
                            'available': max(0, b.to_dict().get('entitled', 0) - b.to_dict().get('used', 0) - b.to_dict().get('pending', 0)),
                        }
                        for b in balances
                    ]
                })
        except Exception:
            emp_balances = []

        return holidays, leaves, employees, weekend_days, emp_balances
