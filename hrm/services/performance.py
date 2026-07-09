from config.firebase import db
from ..audit import enrich_with_audit
from .base import FirestoreService


class PerformanceService(FirestoreService):
    collection_name = 'hrm_review_cycles'

    @classmethod
    def add_review_cycle(cls, data, user):
        doc_id = data.get('doc_id')
        payload = {
            'name': data.get('name'),
            'start_date': data.get('start_date'),
            'end_date': data.get('end_date'),
            'review_type': data.get('review_type', 'Half-Yearly'),
            'status': data.get('status', 'Draft'),
        }
        if doc_id:
            cls.update(doc_id, payload, user)
            return 'updated'
        else:
            cls.create(payload, user)
            return 'created'

    @classmethod
    def add_kpi(cls, data, user):
        doc_id = data.get('doc_id')
        payload = {
            'name': data.get('name'),
            'description': data.get('description', ''),
            'unit': data.get('unit', ''),
            'target_value': data.get('target_value'),
            'default_weight': data.get('default_weight', 1.0),
        }
        if doc_id:
            db.collection('hrm_kpis').document(doc_id).update(
                enrich_with_audit(payload, user, is_update=True)
            )
            return 'updated'
        else:
            db.collection('hrm_kpis').add(
                enrich_with_audit(payload, user, is_update=False)
            )
            return 'created'

    @classmethod
    def add_review(cls, data, user):
        doc_id = data.get('doc_id')
        payload = {
            'employee': data.get('employee'),
            'reviewer': data.get('reviewer'),
            'review_cycle': data.get('review_cycle'),
            'overall_score': data.get('overall_score'),
            'strengths': data.get('strengths', ''),
            'improvements': data.get('improvements', ''),
            'goals': data.get('goals', ''),
            'status': data.get('status', 'Self-Assessment'),
        }
        if doc_id:
            db.collection('hrm_performance_reviews').document(doc_id).update(
                enrich_with_audit(payload, user, is_update=True)
            )
            return 'updated'
        else:
            db.collection('hrm_performance_reviews').add(
                enrich_with_audit(payload, user, is_update=False)
            )
            return 'created'

    @classmethod
    def add_pip(cls, data, user):
        doc_id = data.get('doc_id')
        payload = {
            'employee': data.get('employee'),
            'issue_description': data.get('issue_description', ''),
            'improvement_goals': data.get('improvement_goals', ''),
            'start_date': data.get('start_date'),
            'end_date': data.get('end_date'),
            'status': data.get('status', 'Open'),
        }
        if doc_id:
            db.collection('hrm_pips').document(doc_id).update(
                enrich_with_audit(payload, user, is_update=True)
            )
            return 'updated'
        else:
            db.collection('hrm_pips').add(
                enrich_with_audit(payload, user, is_update=False)
            )
            return 'created'

    @classmethod
    def delete_record(cls, action, doc_id):
        col_map = {
            'delete_review_cycle': 'hrm_review_cycles',
            'delete_kpi': 'hrm_kpis',
            'delete_review': 'hrm_performance_reviews',
            'delete_pip': 'hrm_pips',
        }
        col_name = col_map.get(action)
        if col_name and doc_id:
            db.collection(col_name).document(doc_id).delete()
