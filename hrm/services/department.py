from .base import ORMService
from ..models import Department, Position


class DepartmentService(ORMService):
    model = Department

    @staticmethod
    def _resolve(doc_id, model_class):
        if not doc_id:
            return None
        try:
            return model_class.objects.get(pk=doc_id)
        except (model_class.DoesNotExist, ValueError):
            pass
        return model_class.objects.filter(pk=doc_id).first()

    @classmethod
    def add_department(cls, data, user):
        doc_id = data.get('doc_id')
        if doc_id:
            dept = cls._resolve(doc_id, Department)
            if dept:
                dept.name = data.get('name', dept.name)
                dept.status = data.get('status', 'Active')
                dept.module_linking = data.getlist('module_linking') if hasattr(data, 'getlist') else data.get('module_linking', [])
                dept.notes = data.get('notes', '')
                dept.updated_by = user
                dept.save()
            return 'updated'
        else:
            dept = Department.objects.create(
                name=data.get('name'),
                status=data.get('status', 'Active'),
                module_linking=data.getlist('module_linking') if hasattr(data, 'getlist') else data.get('module_linking', []),
                notes=data.get('notes', ''),
                created_by=user,
                updated_by=user,
            )
            return 'created'

    @classmethod
    def add_sub_department(cls, data, user):
        parent_id = data.get('parent_id')
        if not parent_id:
            return None

        parent = cls._resolve(parent_id, Department)
        if not parent:
            return None

        doc_id = data.get('doc_id')
        if doc_id:
            sub = cls._resolve(doc_id, Department)
            if sub:
                sub.name = data.get('name', sub.name)
                sub.parent = parent
                sub.status = data.get('status', 'Active')
                sub.notes = data.get('notes', '')
                sub.updated_by = user
                sub.save()
            return 'updated'
        else:
            sub = Department.objects.create(
                name=data.get('name'),
                parent=parent,
                status=data.get('status', 'Active'),
                notes=data.get('notes', ''),
                created_by=user,
                updated_by=user,
            )
            return 'created'

    @classmethod
    def add_position(cls, data, user):
        dept_id = data.get('dept_id')
        sub_dept_id = data.get('sub_dept_id', '')
        title = data.get('title')
        status = data.get('status', 'Active')

        if not dept_id or not title:
            return None

        dept = cls._resolve(dept_id, Department)
        if not dept:
            return None

        sub_dept = None
        if sub_dept_id:
            sub_dept = cls._resolve(sub_dept_id, Department)

        doc_id = data.get('doc_id')
        if doc_id:
            pos = cls._resolve(doc_id, Position)
            if pos:
                pos.title = title
                pos.department = dept
                pos.sub_department = sub_dept
                pos.status = status
                pos.save()
            return 'updated'
        else:
            pos = Position.objects.create(
                title=title,
                department=dept,
                sub_department=sub_dept,
                status=status,
            )
            return 'created'

    @classmethod
    def delete_record(cls, action, doc_id):
        model_map = {
            'delete_department': Department,
            'delete_sub_department': Department,
            'delete_position': Position,
        }
        mc = model_map.get(action)
        if mc and doc_id:
            instance = cls._resolve(doc_id, mc)
            if instance:
                instance.is_active = False
                instance.save(update_fields=['is_active'])
