from django.core.cache import cache
from config.logger import hrm_logger


def get_model_data(model_class, filters=None, order_by=None, default_data=None):
    """Fetch data from a Django model with optional filtering and ordering."""
    if default_data is None:
        default_data = []
    try:
        qs = model_class.objects.all()
        if filters:
            qs = qs.filter(**filters)
        if order_by:
            qs = qs.order_by(order_by)
        return list(qs)
    except Exception as e:
        hrm_logger.error(f"Error fetching {model_class.__name__}: {e}")
        return default_data


def get_cached_model_data(model_class, filters=None, order_by=None, default_data=None, timeout=60):
    """Cached wrapper around get_model_data."""
    if default_data is None:
        default_data = []
    cache_key = f'model_{model_class.__name__}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    data = get_model_data(model_class, filters, order_by, default_data)
    cache.set(cache_key, data, timeout)
    return data


def invalidate_model_cache(model_class):
    cache.delete(f'model_{model_class.__name__}')
