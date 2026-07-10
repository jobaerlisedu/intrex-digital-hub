from datetime import datetime
from config.firebase import db


def _now():
    return datetime.now().isoformat()


class SkillsService:
    @staticmethod
    def add_education(data):
        emp_id = data.get('employee_id')
        if not emp_id:
            return None
        doc_id = data.get('doc_id')
        payload = {
            'employee': emp_id,
            'degree': data.get('degree'),
            'institution': data.get('institution'),
            'field_of_study': data.get('field_of_study', ''),
            'start_year': data.get('start_year'),
            'end_year': data.get('end_year'),
            'grade': data.get('grade', ''),
            'is_active': True,
            'updated_at': _now(),
        }
        if doc_id:
            db.collection('hrm_employee_education').document(doc_id).update(payload)
            return 'updated'
        payload['created_at'] = _now()
        db.collection('hrm_employee_education').add(payload)
        return 'created'

    @staticmethod
    def add_experience(data):
        emp_id = data.get('employee_id')
        if not emp_id:
            return None
        doc_id = data.get('doc_id')
        payload = {
            'employee': emp_id,
            'company': data.get('company'),
            'job_title': data.get('job_title'),
            'start_date': data.get('start_date'),
            'end_date': data.get('end_date'),
            'is_current': data.get('is_current') == 'on',
            'description': data.get('description', ''),
            'is_active': True,
            'updated_at': _now(),
        }
        if doc_id:
            db.collection('hrm_employee_experience').document(doc_id).update(payload)
            return 'updated'
        payload['created_at'] = _now()
        db.collection('hrm_employee_experience').add(payload)
        return 'created'

    @staticmethod
    def add_skill(data):
        emp_id = data.get('employee_id')
        skill_name = data.get('skill_name')
        if not emp_id or not skill_name:
            return None
        docs = list(db.collection('hrm_employee_skills')
                    .where('employee', '==', emp_id)
                    .where('skill_name', '==', skill_name)
                    .limit(1).stream())
        payload = {
            'employee': emp_id,
            'skill_name': skill_name,
            'proficiency': data.get('proficiency', 'Intermediate'),
            'years_of_experience': data.get('years_of_experience'),
            'is_active': True,
            'updated_at': _now(),
        }
        if docs:
            db.collection('hrm_employee_skills').document(docs[0].id).update(payload)
        else:
            payload['created_at'] = _now()
            db.collection('hrm_employee_skills').add(payload)
        return 'created'

    @staticmethod
    def add_competency_rating(data):
        emp_id = data.get('employee_id')
        comp_id = data.get('competency_id')
        if not emp_id or not comp_id:
            return None
        docs = list(db.collection('hrm_competency_ratings')
                    .where('employee', '==', emp_id)
                    .where('competency', '==', comp_id)
                    .limit(1).stream())
        payload = {
            'employee': emp_id,
            'competency': comp_id,
            'rating': data.get('rating'),
            'assessed_by': data.get('assessed_by'),
            'assessment_date': _now()[:10],
            'notes': data.get('notes', ''),
            'is_active': True,
            'updated_at': _now(),
        }
        if docs:
            db.collection('hrm_competency_ratings').document(docs[0].id).update(payload)
        else:
            payload['created_at'] = _now()
            db.collection('hrm_competency_ratings').add(payload)
        return 'created'
