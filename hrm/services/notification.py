from django.utils import timezone
from ..models import Notification, NotificationPreference, DeviceToken


class NotificationService:
    @staticmethod
    def get_unread_count(user):
        return Notification.objects.filter(recipient=user, is_read=False, is_active=True).count()

    @staticmethod
    def mark_read(notification_id, user):
        Notification.objects.filter(id=notification_id, recipient=user, is_active=True).update(is_read=True, read_at=timezone.now())

    @staticmethod
    def mark_all_read(user):
        Notification.objects.filter(recipient=user, is_read=False, is_active=True).update(is_read=True, read_at=timezone.now())

    @staticmethod
    def update_preferences(user, data):
        pref, _ = NotificationPreference.objects.get_or_create(user=user)
        for field in ('notify_in_app', 'notify_email', 'notify_push'):
            if field in data:
                setattr(pref, field, data[field] == 'on')
        pref.digest_frequency = data.get('digest_frequency', pref.digest_frequency)
        pref.save()

    @staticmethod
    def get_notifications(user):
        return Notification.objects.filter(recipient=user, is_active=True).order_by('-created_at')[:50]
