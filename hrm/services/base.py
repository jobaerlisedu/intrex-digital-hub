from config.firebase import db
from google.cloud import firestore
from django.core.cache import cache
from config.logger import hrm_logger
from ..audit import enrich_with_audit
from ..views_helpers import get_collection_data, get_cached_collection, invalidate_cache
from django.contrib import messages
from django.shortcuts import redirect


class FirestoreService:
    collection_name = None
    cache_enabled = False

    @classmethod
    def _col(cls):
        return db.collection(cls.collection_name)

    @classmethod
    def get_all(cls, default=None):
        return get_collection_data(cls.collection_name, default or [])

    @classmethod
    def get_cached(cls, timeout=60):
        return get_cached_collection(cls.collection_name, timeout=timeout)

    @classmethod
    def get_by_id(cls, doc_id):
        doc = cls._col().document(doc_id).get()
        if doc.exists:
            item = doc.to_dict()
            item['id'] = doc.id
            return item
        return None

    @classmethod
    def create(cls, data, user):
        data = enrich_with_audit(data, user, is_update=False)
        _, ref = cls._col().add(data)
        if cls.cache_enabled:
            invalidate_cache(cls.collection_name)
        return ref.id

    @classmethod
    def update(cls, doc_id, data, user):
        data = enrich_with_audit(data, user, is_update=True)
        cls._col().document(doc_id).update(data)
        if cls.cache_enabled:
            invalidate_cache(cls.collection_name)

    @classmethod
    def delete(cls, doc_id):
        cls._col().document(doc_id).delete()
        if cls.cache_enabled:
            invalidate_cache(cls.collection_name)

    @classmethod
    def update_status(cls, doc_id, status, user):
        cls._col().document(doc_id).update(
            enrich_with_audit({'status': status}, user, is_update=True)
        )

    @classmethod
    def get_employee_list(cls):
        try:
            docs = db.collection('hrm_employees').stream()
            return [d.to_dict().get('name', '') for d in docs if d.to_dict().get('name')]
        except Exception:
            return []

    @classmethod
    def validate_and_act(cls, request, validator, on_success, redirect_name, form_data=None):
        data = form_data or request.POST
        errors = validator(data) if validator else []
        if errors:
            for e in errors:
                messages.error(request, e)
            return redirect(redirect_name)
        try:
            result = on_success()
            return result
        except Exception as e:
            hrm_logger.error(f"Error in {cls.__name__}: {e}")
            messages.error(request, str(e))
            return redirect(redirect_name)
