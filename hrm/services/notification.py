from datetime import datetime
from config.firebase import db


class NotificationService:
    @staticmethod
    def get_unread_count(user):
        docs = list(db.collection('hrm_notifications')
                    .where('recipient', '==', f'users/{user.id}')
                    .where('is_read', '==', False)
                    .where('is_active', '==', True)
                    .limit(100).stream())
        return len(docs)

    @staticmethod
    def mark_read(notification_id, user):
        db.collection('hrm_notifications').document(notification_id).update({
            'is_read': True,
            'read_at': datetime.now().isoformat(),
        })

    @staticmethod
    def mark_all_read(user):
        docs = db.collection('hrm_notifications')\
            .where('recipient', '==', f'users/{user.id}')\
            .where('is_read', '==', False)\
            .where('is_active', '==', True).stream()
        now = datetime.now().isoformat()
        for d in docs:
            db.collection('hrm_notifications').document(d.id).update({
                'is_read': True,
                'read_at': now,
            })

    @staticmethod
    def update_preferences(user, data):
        docs = list(db.collection('hrm_notification_preferences')
                    .where('user', '==', f'users/{user.id}')
                    .limit(1).stream())
        payload = {
            'notify_in_app': data.get('notify_in_app', 'on') == 'on',
            'notify_email': data.get('notify_email', '') == 'on',
            'notify_push': data.get('notify_push', '') == 'on',
            'digest_frequency': data.get('digest_frequency', 'instant'),
            'updated_at': datetime.now().isoformat(),
        }
        if docs:
            db.collection('hrm_notification_preferences').document(docs[0].id).update(payload)
        else:
            payload['user'] = f'users/{user.id}'
            payload['created_at'] = datetime.now().isoformat()
            db.collection('hrm_notification_preferences').add(payload)

    @staticmethod
    def get_notifications(user):
        return [
            {'id': d.id, **d.to_dict()}
            for d in db.collection('hrm_notifications')
            .where('recipient', '==', f'users/{user.id}')
            .where('is_active', '==', True)
            .order_by('created_at', direction='DESCENDING')
            .limit(50).stream()
        ]
