from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User, Group
from django.contrib.auth.hashers import check_password
from config.firebase import db

class FirestoreBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        try:
            user_doc_ref = db.collection('sys_users').document(username)
            user_doc = user_doc_ref.get()

            if not user_doc.exists:
                return None

            data = user_doc.to_dict()
            firestore_hash = data.get('password')

            if not firestore_hash or not check_password(password, firestore_hash):
                return None

            user, _ = User.objects.get_or_create(username=username, defaults={
                'email': data.get('email', ''),
                'first_name': data.get('first_name', ''),
                'last_name': data.get('last_name', ''),
                'is_staff': data.get('is_staff', False),
                'is_superuser': data.get('is_superuser', False),
                'is_active': data.get('is_active', True),
            })
            user.email = data.get('email', '')
            user.first_name = data.get('first_name', '')
            user.last_name = data.get('last_name', '')
            user.is_staff = data.get('is_staff', False)
            user.is_superuser = data.get('is_superuser', False)
            user.is_active = data.get('is_active', True)
            user.save()

            user.groups.clear()
            for group_name in data.get('groups', []):
                group, _ = Group.objects.get_or_create(name=group_name)
                user.groups.add(group)

            return user

        except Exception as e:
            print(f"Error in FirestoreBackend authentication: {e}")
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
