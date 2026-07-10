from config.firebase import db
from datetime import datetime


class HRMSettingsService:
    @staticmethod
    def save_setting(key, value):
        docs = list(db.collection('hrm_settings').where('key', '==', key).limit(1).stream())
        payload = {'value': value, 'is_active': True, 'updated_at': datetime.now().isoformat()}
        if docs:
            db.collection('hrm_settings').document(docs[0].id).update(payload)
        else:
            payload['key'] = key
            payload['created_at'] = datetime.now().isoformat()
            db.collection('hrm_settings').add(payload)

    @staticmethod
    def add_leave_policy(data):
        doc_id = data.get('doc_id')
        payload = {
            'employee_type': data.get('employee_type'),
            'leave_type': data.get('leave_type'),
            'entitled_days': float(data.get('entitled_days', 0)),
            'carry_forward_days': float(data.get('carry_forward_days', 0)),
            'is_active': True,
            'updated_at': datetime.now().isoformat(),
        }
        if doc_id:
            db.collection('hrm_leave_policies').document(doc_id).update(payload)
            return 'updated'
        payload['created_at'] = datetime.now().isoformat()
        db.collection('hrm_leave_policies').add(payload)
        return 'created'

    @staticmethod
    def add_rating_template(data):
        doc_id = data.get('doc_id')
        payload = {
            'name': data.get('name'),
            'description': data.get('description', ''),
            'is_active': True,
            'updated_at': datetime.now().isoformat(),
        }
        if doc_id:
            db.collection('hrm_rating_templates').document(doc_id).update(payload)
            return 'updated'
        payload['scales'] = []
        payload['created_at'] = datetime.now().isoformat()
        db.collection('hrm_rating_templates').add(payload)
        return 'created'
