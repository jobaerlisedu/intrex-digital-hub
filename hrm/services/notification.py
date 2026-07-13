from ..models import Notification, NotificationPreference


class NotificationService:
    @staticmethod
    def get_unread_count(user):
        return Notification.objects.filter(recipient=user, is_read=False, is_active=True).count()

    @staticmethod
    def mark_read(notification_id, user):
        Notification.objects.filter(pk=notification_id, recipient=user).update(is_read=True)
        try:
            n = Notification.objects.get(pk=notification_id, recipient=user)
            n.is_read = True
            n.save(update_fields=['is_read'])
        except (Notification.DoesNotExist, ValueError):
            pass

    @staticmethod
    def mark_all_read(user):
        Notification.objects.filter(recipient=user, is_read=False, is_active=True).update(is_read=True)

    @staticmethod
    def update_preferences(user, data):
        prefs, _ = NotificationPreference.objects.get_or_create(user=user)
        prefs.notify_in_app = data.get('notify_in_app', 'on') == 'on'
        prefs.notify_email = data.get('notify_email', '') == 'on'
        prefs.notify_push = data.get('notify_push', '') == 'on'
        prefs.digest_frequency = data.get('digest_frequency', 'instant')
        prefs.save()

    @staticmethod
    def get_notifications(user):
        return list(Notification.objects.filter(recipient=user, is_active=True).order_by('-created_at')[:50])
