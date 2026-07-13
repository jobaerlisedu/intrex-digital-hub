from django.db import models
from config.logger import hrm_logger


class ORMService:
    model = None
    search_field = 'pk'

    @classmethod
    def get_all(cls, filters=None, order_by=None):
        qs = cls.model.objects.all()
        if filters:
            qs = qs.filter(**filters)
        if order_by:
            qs = qs.order_by(order_by)
        return list(qs)

    @classmethod
    def get_by_id(cls, pk):
        try:
            return cls.model.objects.get(pk=pk)
        except cls.model.DoesNotExist:
            return None

    @classmethod
    def create(cls, data, user=None):
        instance = cls.model(**data)
        if user:
            instance.created_by = user
            instance.updated_by = user
        instance.save()
        return str(instance.pk)

    @classmethod
    def update(cls, pk, data, user=None):
        if user:
            data['updated_by'] = user
        cls.model.objects.filter(pk=pk).update(**data)
        return pk

    @classmethod
    def delete(cls, pk, soft=True):
        if soft:
            cls.model.objects.filter(pk=pk).update(is_active=False)
        else:
            cls.model.objects.filter(pk=pk).delete()

    @classmethod
    def update_status(cls, pk, status, user=None):
        data = {'status': status}
        if user:
            data['updated_by'] = user
        cls.model.objects.filter(pk=pk).update(**data)

    @classmethod
    def get_employee_list(cls):
        try:
            from ..models import Employee
            return [e.name for e in Employee.objects.filter(is_active=True) if e.name]
        except Exception:
            return []

    @classmethod
    def get_or_create_by_pk(cls, model_class, pk, defaults=None):
        if not pk:
            return None
        try:
            obj, _ = model_class.objects.get_or_create(
                pk=pk,
                defaults=defaults or {},
            )
            return obj
        except model_class.MultipleObjectsReturned:
            return model_class.objects.filter(pk=pk).first()
