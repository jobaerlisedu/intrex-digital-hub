from config.firebase import db
from google.cloud import firestore
from django.core.cache import cache
from config.logger import hrm_logger


def get_collection_data(collection_name, default_data=None):
    if default_data is None:
        default_data = []
    try:
        docs = db.collection(collection_name).order_by('createdAt', direction=firestore.Query.DESCENDING).stream()
        results = []
        for doc in docs:
            item = doc.to_dict()
            item['id'] = doc.id
            results.append(item)
        if not results:
            return default_data
        return results
    except Exception as e:
        hrm_logger.error(f"Error fetching {collection_name}: {e}")
        return default_data


def get_cached_collection(collection_name, default_data=None, timeout=60):
    if default_data is None:
        default_data = []
    cache_key = f'firestore_{collection_name}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    data = get_collection_data(collection_name, default_data)
    cache.set(cache_key, data, timeout)
    return data


def invalidate_cache(collection_name):
    cache.delete(f'firestore_{collection_name}')
