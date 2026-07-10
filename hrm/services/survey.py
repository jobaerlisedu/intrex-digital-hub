from datetime import datetime
from config.firebase import db


class SurveyService:
    @staticmethod
    def add_survey(data):
        doc_id = data.get('doc_id')
        payload = {
            'title': data.get('title'),
            'description': data.get('description', ''),
            'start_date': data.get('start_date'),
            'end_date': data.get('end_date'),
            'is_anonymous': data.get('is_anonymous') == 'on',
            'status': data.get('status', 'Draft'),
            'is_active': True,
            'updated_at': datetime.now().isoformat(),
        }
        if doc_id:
            db.collection('hrm_surveys').document(doc_id).update(payload)
            return 'updated'
        payload['created_at'] = datetime.now().isoformat()
        db.collection('hrm_surveys').add(payload)
        return 'created'
