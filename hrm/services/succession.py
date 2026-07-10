from datetime import datetime
from config.firebase import db


class SuccessionService:
    KEY_POSITIONS = 'hrm_key_positions'
    SUCCESSORS = 'hrm_successor_candidates'
    PLANS = 'hrm_succession_plans'

    @staticmethod
    def _payload(data, extra=None):
        now = datetime.now().isoformat()
        p = {
            'position_title': data.get('position_title'),
            'risk_of_vacancy': data.get('risk_of_vacancy'),
            'readiness_gap': data.get('readiness_gap'),
            'status': data.get('status', 'Active'),
            'updated_at': now,
        }
        if extra:
            p.update(extra)
        return p

    @staticmethod
    def add_key_position(data):
        doc_id = data.get('doc_id')
        now = datetime.now().isoformat()
        if doc_id:
            db.collection(SuccessionService.KEY_POSITIONS).document(doc_id).update({
                'position_title': data.get('position_title'),
                'risk_of_vacancy': data.get('risk_of_vacancy'),
                'readiness_gap': data.get('readiness_gap'),
                'status': data.get('status', 'Active'),
                'updated_at': now,
            })
            return 'updated'
        else:
            db.collection(SuccessionService.KEY_POSITIONS).add({
                'position_title': data.get('position_title'),
                'risk_of_vacancy': data.get('risk_of_vacancy'),
                'readiness_gap': data.get('readiness_gap'),
                'status': data.get('status', 'Active'),
                'is_active': True,
                'created_at': now,
                'updated_at': now,
            })
            return 'created'

    @staticmethod
    def add_successor(data):
        succ_id = data.get('id')
        now = datetime.now().isoformat()
        if succ_id:
            db.collection(SuccessionService.SUCCESSORS).document(succ_id).update({
                'readiness': data.get('readiness'),
                'strengths': data.get('strengths', ''),
                'development_needs': data.get('development_needs', ''),
                'is_primary': data.get('is_primary') == 'on',
                'updated_at': now,
            })
            return 'updated'
        else:
            kp_id = data.get('key_position_id')
            emp_id = data.get('employee_id')
            if kp_id and emp_id:
                db.collection(SuccessionService.SUCCESSORS).add({
                    'key_position': f'hrm_key_positions/{kp_id}',
                    'employee': f'hrm_employees/{emp_id}',
                    'readiness': data.get('readiness'),
                    'strengths': data.get('strengths', ''),
                    'development_needs': data.get('development_needs', ''),
                    'is_primary': data.get('is_primary') == 'on',
                    'is_active': True,
                    'created_at': now,
                    'updated_at': now,
                })
                return 'created'
        return None

    @staticmethod
    def add_plan(data):
        doc_id = data.get('doc_id')
        now = datetime.now().isoformat()
        if doc_id:
            db.collection(SuccessionService.PLANS).document(doc_id).update({
                'title': data.get('title'),
                'description': data.get('description', ''),
                'review_date': data.get('review_date'),
                'status': data.get('status', 'Draft'),
                'updated_at': now,
            })
            return 'updated'
        else:
            db.collection(SuccessionService.PLANS).add({
                'title': data.get('title'),
                'description': data.get('description', ''),
                'review_date': data.get('review_date'),
                'status': data.get('status', 'Draft'),
                'is_active': True,
                'created_at': now,
                'updated_at': now,
            })
            return 'created'
