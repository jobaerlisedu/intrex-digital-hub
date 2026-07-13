celery_app = None
try:
    from .celery import app as celery_app
except (ImportError, KeyError):
    pass
__all__ = ('celery_app',)
