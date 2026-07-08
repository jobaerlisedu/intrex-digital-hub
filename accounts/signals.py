from django.contrib.auth.models import User
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from config.logger import accounts_logger


def _user_to_firestore_dict(user):
    return {
        'username': user.username,
        'email': user.email,
        'password': user.password,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
        'is_active': user.is_active,
        'groups': list(user.groups.values_list('name', flat=True)),
    }


def _sync_user_to_firestore(user):
    try:
        from config.firebase import db
        data = _user_to_firestore_dict(user)
        db.collection('sys_users').document(user.username).set(data)
    except Exception as e:
        accounts_logger.warning(f"Could not sync user '{user.username}' to Firestore: {e}")


def _remove_user_from_firestore(user):
    try:
        from config.firebase import db
        doc_ref = db.collection('sys_users').document(user.username)
        if doc_ref.get().exists:
            doc_ref.delete()
    except Exception as e:
        accounts_logger.warning(f"Could not remove user '{user.username}' from Firestore: {e}")


@receiver(post_save, sender=User)
def sync_user_post_save(sender, instance, created, **kwargs):
    _sync_user_to_firestore(instance)


@receiver(pre_delete, sender=User)
def sync_user_pre_delete(sender, instance, **kwargs):
    _remove_user_from_firestore(instance)
