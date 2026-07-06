from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User, Group
from django.contrib.auth.hashers import check_password
from config.firebase import db

class FirestoreBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        try:
            user = User.objects.get(username=username)
            if user.check_password(password):
                self._sync_profile_to_firestore(user)
                return user
        except User.DoesNotExist:
            pass

        return None

    def _sync_profile_to_firestore(self, user):
        try:
            db.collection('sys_users').document(user.username).set({
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'is_active': user.is_active,
                'groups': [g.name for g in user.groups.all()]
            }, merge=True)
        except Exception as e:
            print(f"Error syncing profile to Firestore for '{user.username}': {e}")

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

def sync_users_from_firestore():
    """Sync user profile data from Firestore into the local SQLite database."""
    try:
        users_ref = db.collection('sys_users').stream()
        for doc in users_ref:
            data = doc.to_dict()
            username = doc.id
            if not username:
                continue

            email = data.get('email', '')
            first_name = data.get('first_name', '')
            last_name = data.get('last_name', '')
            is_staff = data.get('is_staff', False)
            is_superuser = data.get('is_superuser', False)
            is_active = data.get('is_active', True)
            group_names = data.get('groups', [])

            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                user = User(username=username)
                user.set_unusable_password()

            user._syncing = True
            user.email = email
            user.first_name = first_name
            user.last_name = last_name
            user.is_staff = is_staff
            user.is_superuser = is_superuser
            user.is_active = is_active
            user.save()

            user.groups.clear()
            for group_name in group_names:
                group, _ = Group.objects.get_or_create(name=group_name)
                user.groups.add(group)
    except Exception as e:
        print(f"Error syncing users from Firestore: {e}")
