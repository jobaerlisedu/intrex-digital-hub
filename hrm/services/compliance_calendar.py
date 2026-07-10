from datetime import datetime
from config.firebase import db


class ComplianceCalendarService:
    @staticmethod
    def add_reminder(data):
        emp_id = data.get('employee_id')
        if not emp_id:
            return None
        doc_id = data.get('doc_id')
        payload = {
            'employee': emp_id,
            'reminder_type': data.get('reminder_type'),
            'title': data.get('title'),
            'description': data.get('description', ''),
            'due_date': data.get('due_date'),
            'status': data.get('status', 'Pending'),
            'completed_date': None,
            'is_active': True,
            'updated_at': datetime.now().isoformat(),
        }
        if doc_id:
            db.collection('hrm_compliance_reminders').document(doc_id).update(payload)
            return 'updated'
        payload['created_at'] = datetime.now().isoformat()
        db.collection('hrm_compliance_reminders').add(payload)
        return 'created'
