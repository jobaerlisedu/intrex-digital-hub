from .base import ORMService
from ..models import Document, Asset, Employee


class DocumentAssetService(ORMService):
    model = Document

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
    def add_document(cls, data, user):
        emp_name = data.get('employee')
        emp = Employee.objects.filter(name=emp_name).first()
        instance = Document.objects.create(
            employee=emp,
            document_type=data.get('document_type'),
            document_number=data.get('document_number', ''),
            expiry_date=data.get('expiry_date') or None,
        )
    @classmethod
    def delete_document(cls, doc_id):
        instance = cls._resolve(doc_id, Document)
        if instance:
            instance.is_active = False
            instance.save(update_fields=['is_active'])

    @classmethod
    def assign_asset(cls, data, user):
        emp_name = data.get('employee')
        emp = Employee.objects.filter(name=emp_name).first()
        instance = Asset.objects.create(
            employee=emp,
            asset_name=data.get('asset_name'),
            asset_tag=data.get('asset_tag', ''),
            serial_number=data.get('serial_number', ''),
            status='Assigned',
        )
    @classmethod
    def return_asset(cls, doc_id, user):
        instance = cls._resolve(doc_id, Asset)
        if instance:
            instance.status = 'Returned'
            instance.save(update_fields=['status'])
