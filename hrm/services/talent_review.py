from datetime import datetime
from config.firebase import db


class TalentReviewService:
    @staticmethod
    def add_meeting(data):
        doc_id = data.get('doc_id')
        payload = {
            'title': data.get('title'),
            'meeting_date': data.get('meeting_date'),
            'notes': data.get('notes', ''),
            'status': data.get('status', 'Draft'),
            'is_active': True,
            'updated_at': datetime.now().isoformat(),
        }
        if doc_id:
            db.collection('hrm_talent_review_meetings').document(doc_id).update(payload)
            return 'updated'
        payload['created_at'] = datetime.now().isoformat()
        db.collection('hrm_talent_review_meetings').add(payload)
        return 'created'

    @staticmethod
    def set_nine_box(data):
        meeting_id = data.get('meeting_id')
        emp_id = data.get('employee_id')
        if not meeting_id or not emp_id:
            return None
        docs = list(db.collection('hrm_nine_box_cells')
                    .where('talent_review', '==', meeting_id)
                    .where('employee', '==', emp_id)
                    .limit(1).stream())
        payload = {
            'talent_review': meeting_id,
            'employee': emp_id,
            'performance': data.get('performance'),
            'potential': data.get('potential'),
            'notes': data.get('notes', ''),
            'is_active': True,
            'updated_at': datetime.now().isoformat(),
        }
        if docs:
            db.collection('hrm_nine_box_cells').document(docs[0].id).update(payload)
        else:
            payload['created_at'] = datetime.now().isoformat()
            db.collection('hrm_nine_box_cells').add(payload)
        return 'saved'
