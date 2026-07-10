from datetime import datetime
from config.firebase import db


class FeedbackService:
    @staticmethod
    def add_question(data):
        db.collection('hrm_feedback_questions').add({
            'category': data.get('category'),
            'question_text': data.get('question_text'),
            'is_required': data.get('is_required') == 'on',
            'order': int(data.get('order', 0)),
            'is_active': True,
            'created_at': datetime.now().isoformat(),
        })
        return 'created'

    @staticmethod
    def add_request(data):
        reviewer_id = data.get('reviewer_id')
        reviewee_id = data.get('reviewee_id')
        if not reviewer_id or not reviewee_id:
            return None
        docs = list(db.collection('hrm_feedback_requests')
                    .where('reviewer', '==', reviewer_id)
                    .where('reviewee', '==', reviewee_id)
                    .limit(1).stream())
        payload = {
            'reviewer': reviewer_id,
            'reviewee': reviewee_id,
            'review_cycle_id': data.get('review_cycle_id'),
            'relationship': data.get('relationship', ''),
            'status': data.get('status', 'Pending'),
            'due_date': data.get('due_date'),
            'is_active': True,
            'updated_at': datetime.now().isoformat(),
        }
        if docs:
            db.collection('hrm_feedback_requests').document(docs[0].id).update(payload)
        else:
            payload['created_at'] = datetime.now().isoformat()
            db.collection('hrm_feedback_requests').add(payload)
        return 'created'
