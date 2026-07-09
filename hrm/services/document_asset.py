from config.firebase import db
from ..audit import enrich_with_audit
from .base import FirestoreService


class DocumentAssetService(FirestoreService):
    collection_name = 'hrm_documents'

    @classmethod
    def add_document(cls, data, user):
        cls.create({
            'employee': data.get('employee'),
            'document_type': data.get('document_type'),
            'document_number': data.get('document_number', ''),
            'expiry_date': data.get('expiry_date'),
        }, user)

    @classmethod
    def delete_document(cls, doc_id):
        cls.delete(doc_id)

    @classmethod
    def assign_asset(cls, data, user):
        db.collection('hrm_assets').add(
            enrich_with_audit({
                'employee': data.get('employee'),
                'asset_name': data.get('asset_name'),
                'asset_tag': data.get('asset_tag', ''),
                'serial_number': data.get('serial_number', ''),
                'status': 'Assigned',
            }, user, is_update=False)
        )

    @classmethod
    def return_asset(cls, doc_id, user):
        db.collection('hrm_assets').document(doc_id).update(
            enrich_with_audit({'status': 'Returned'}, user, is_update=True)
        )
