from config.firebase import db
from config.logger import hrm_logger
from ..audit import enrich_with_audit
from ..validators import validate_department_data, validate_position_data
from ..views_helpers import invalidate_cache
from .base import FirestoreService


class DepartmentService(FirestoreService):
    collection_name = 'org_departments'
    cache_enabled = True

    @classmethod
    def add_department(cls, data, user):
        doc_id = data.get('doc_id')
        base_data = {
            'name': data.get('name'),
            'status': data.get('status', 'Active'),
            'module_linking': data.getlist('module_linking') if hasattr(data, 'getlist') else data.get('module_linking', []),
            'notes': data.get('notes', ''),
        }
        if doc_id:
            cls.update(doc_id, base_data, user)
            return 'updated'
        else:
            cls.create(base_data, user)
            return 'created'

    @classmethod
    def add_sub_department(cls, data, user):
        parent_id = data.get('parent_id')
        if not parent_id:
            return None

        name = data.get('name')
        status = data.get('status', 'Active')
        notes = data.get('notes', '')

        parent_name = None
        parent_doc = db.collection('org_departments').document(parent_id).get()
        if parent_doc.exists:
            parent_name = parent_doc.to_dict().get('name')

        if not parent_name:
            return None

        doc_id = data.get('doc_id')
        base_data = {
            'name': name,
            'parent_id': parent_id,
            'parent_name': parent_name,
            'status': status,
            'notes': notes,
        }

        if doc_id:
            db.collection('org_departments_sub').document(doc_id).update(
                enrich_with_audit(base_data, user, is_update=True)
            )
            result = 'updated'
        else:
            db.collection('org_departments_sub').add(
                enrich_with_audit(base_data, user, is_update=False)
            )
            result = 'created'

        invalidate_cache('org_departments_sub')
        return result

    @classmethod
    def add_position(cls, data, user):
        dept_id = data.get('dept_id')
        sub_dept_id = data.get('sub_dept_id', '')
        title = data.get('title')
        status = data.get('status', 'Active')

        if not dept_id or not title:
            return None

        dept_name = None
        dept_doc = db.collection('org_departments').document(dept_id).get()
        if dept_doc.exists:
            dept_name = dept_doc.to_dict().get('name')

        if not dept_name:
            return None

        sub_dept_name = "None"
        if sub_dept_id:
            sub_dept_doc = db.collection('org_departments_sub').document(sub_dept_id).get()
            if sub_dept_doc.exists:
                sub_dept_name = sub_dept_doc.to_dict().get('name')
        else:
            sub_dept_id = ""

        doc_id = data.get('doc_id')
        base_data = {
            'title': title,
            'dept_id': dept_id,
            'dept_name': dept_name,
            'sub_dept_id': sub_dept_id,
            'sub_dept_name': sub_dept_name,
            'status': status,
        }

        if doc_id:
            cls.update(doc_id, base_data, user)
            result = 'updated'
        else:
            cls.create(base_data, user)
            result = 'created'

        invalidate_cache('org_positions')
        return result

    @classmethod
    def delete_record(cls, action, doc_id):
        col_map = {
            'delete_department': 'org_departments',
            'delete_sub_department': 'org_departments_sub',
            'delete_position': 'org_positions',
        }
        col_name = col_map.get(action)
        if col_name and doc_id:
            db.collection(col_name).document(doc_id).delete()
            invalidate_cache(col_name)
