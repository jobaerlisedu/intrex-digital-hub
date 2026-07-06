from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from config.firebase import db

@receiver(post_save, sender=User)
def sync_user_to_firestore(sender, instance, created, **kwargs):
    # Skip if the user is currently being synced from firestore to avoid infinite loops
    if getattr(instance, '_syncing', False):
        return

    try:
        user_data = {
            'username': instance.username,
            'email': instance.email,
            'first_name': instance.first_name,
            'last_name': instance.last_name,
            'is_staff': instance.is_staff,
            'is_superuser': instance.is_superuser,
            'is_active': instance.is_active,
            'groups': [g.name for g in instance.groups.all()]
        }
        # Save or update document in Firestore
        db.collection('sys_users').document(instance.username).set(user_data)
        print(f"Successfully synced user '{instance.username}' to Firestore.")
    except Exception as e:
        print(f"Error syncing user '{instance.username}' to Firestore: {e}")

@receiver(post_delete, sender=User)
def delete_user_from_firestore(sender, instance, **kwargs):
    try:
        db.collection('sys_users').document(instance.username).delete()
        print(f"Successfully deleted user '{instance.username}' from Firestore.")
    except Exception as e:
        print(f"Error deleting user '{instance.username}' from Firestore: {e}")
