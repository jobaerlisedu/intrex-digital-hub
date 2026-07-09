import random
from config.firebase import db
from config.logger import hrm_logger
from ..audit import enrich_with_audit
from ..validators import validate_candidate_data
from .base import FirestoreService


class RecruitmentService(FirestoreService):
    collection_name = 'hrm_recruitment_candidates'

    @classmethod
    def add_candidate(cls, data, user):
        doc_id = data.get('doc_id')
        from datetime import datetime
        today_str = datetime.now().strftime('%Y-%m-%d')
        date_applied = data.get('date_applied') or today_str

        update_data = {
            'name': data.get('name'),
            'position': data.get('position'),
            'status': data.get('status', 'New'),
            'notes': data.get('notes', ''),
            'date_applied': date_applied,
        }

        if doc_id:
            cls.update(doc_id, update_data, user)
            return 'updated'
        else:
            cand_id = f"CAN-{random.randint(100, 999)}"
            update_data['cand_id'] = cand_id
            cls.create(update_data, user)
            return 'created'

    @classmethod
    def add_shortlist(cls, data, user):
        cand_doc_id = data.get('candidate_id')
        if not cand_doc_id:
            return None

        cand_ref = db.collection('hrm_recruitment_candidates').document(cand_doc_id)
        cand_doc = cand_ref.get()
        if not cand_doc.exists:
            return None

        cand_info = cand_doc.to_dict()
        cand_name = cand_info.get('name')
        cand_position = cand_info.get('position')
        cand_ref.update({'status': 'Shortlisted'})

        if not cand_name:
            return None

        doc_id = data.get('doc_id')
        base_data = {
            'candidate_id': cand_doc_id,
            'name': cand_name,
            'position': cand_position,
            'rating': data.get('rating'),
            'experience': data.get('experience'),
        }

        if doc_id:
            db.collection('hrm_recruitment_shortlists').document(doc_id).update(
                enrich_with_audit(base_data, user, is_update=True)
            )
            return 'updated'
        else:
            db.collection('hrm_recruitment_shortlists').add(
                enrich_with_audit(base_data, user, is_update=False)
            )
            return 'created'

    @classmethod
    def add_interview(cls, data, user):
        cand_doc_id = data.get('candidate_id')
        if not cand_doc_id:
            return None

        cand_ref = db.collection('hrm_recruitment_candidates').document(cand_doc_id)
        cand_doc = cand_ref.get()
        if not cand_doc.exists:
            return None

        cand_info = cand_doc.to_dict()
        cand_name = cand_info.get('name')
        cand_position = cand_info.get('position')
        cand_ref.update({'status': 'Interview'})

        if not cand_name:
            return None

        doc_id = data.get('doc_id')
        base_data = {
            'candidate_id': cand_doc_id,
            'name': cand_name,
            'position': cand_position,
            'interviewer': data.get('interviewer'),
            'date_time': data.get('date_time'),
            'status': data.get('status', 'Scheduled'),
        }

        if doc_id:
            db.collection('hrm_recruitment_interviews').document(doc_id).update(
                enrich_with_audit(base_data, user, is_update=True)
            )
            return 'updated'
        else:
            db.collection('hrm_recruitment_interviews').add(
                enrich_with_audit(base_data, user, is_update=False)
            )
            return 'created'

    @classmethod
    def add_selection(cls, data, user):
        cand_doc_id = data.get('candidate_id')
        if not cand_doc_id:
            return None

        cand_ref = db.collection('hrm_recruitment_candidates').document(cand_doc_id)
        cand_doc = cand_ref.get()
        if not cand_doc.exists:
            return None

        cand_info = cand_doc.to_dict()
        cand_name = cand_info.get('name')
        cand_position = cand_info.get('position')
        offer_status = data.get('offer_status')
        new_status = 'Selected' if offer_status in ['Offered', 'Accepted', 'Joined'] else 'Rejected'
        cand_ref.update({'status': new_status})

        if not cand_name:
            return None

        doc_id = data.get('doc_id')
        base_data = {
            'candidate_id': cand_doc_id,
            'name': cand_name,
            'position': cand_position,
            'offer_status': offer_status,
            'offer_date': data.get('offer_date'),
        }

        if doc_id:
            db.collection('hrm_recruitment_selections').document(doc_id).update(
                enrich_with_audit(base_data, user, is_update=True)
            )
            return 'updated'
        else:
            db.collection('hrm_recruitment_selections').add(
                enrich_with_audit(base_data, user, is_update=False)
            )
            return 'created'

    @classmethod
    def delete_record(cls, action, doc_id):
        col_map = {
            'delete_candidate': 'hrm_recruitment_candidates',
            'delete_shortlist': 'hrm_recruitment_shortlists',
            'delete_interview': 'hrm_recruitment_interviews',
            'delete_selection': 'hrm_recruitment_selections',
        }
        col_name = col_map.get(action)
        if col_name and doc_id:
            db.collection(col_name).document(doc_id).delete()

    @classmethod
    def get_candidates(cls):
        from ..views_helpers import get_collection_data, get_cached_collection
        candidates = get_collection_data('hrm_recruitment_candidates', [])
        shortlists = get_collection_data('hrm_recruitment_shortlists', [])
        interviews = get_collection_data('hrm_recruitment_interviews', [])
        selections = get_collection_data('hrm_recruitment_selections', [])
        positions_data = get_cached_collection('org_positions')
        departments = get_cached_collection('org_departments')
        sub_departments = get_cached_collection('org_departments_sub')

        positions = []
        for p in positions_data:
            title = p.get('title') or p.get('name')
            if title:
                positions.append({
                    'title': title,
                    'dept_name': p.get('dept_name', ''),
                    'sub_dept_name': p.get('sub_dept_name', '')
                })

        return candidates, shortlists, interviews, selections, positions, departments, sub_departments
