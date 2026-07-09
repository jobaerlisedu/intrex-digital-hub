from django.apps import AppConfig


class HrmConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'hrm'

    def ready(self):
        from config.services.notification_service import init_event_subscribers
        init_event_subscribers()
