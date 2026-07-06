import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from config.firebase import db
from django.contrib.auth.hashers import make_password

try:
    admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
    admin_email = os.environ.get('ADMIN_EMAIL', 'admin@intrex.com')
    admin_hash = make_password(admin_password)

    db.collection('sys_users').document('admin').set({
        'username': 'admin',
        'email': admin_email,
        'password': admin_hash,
        'first_name': 'Super',
        'last_name': 'Admin',
        'is_staff': True,
        'is_superuser': True,
        'is_active': True,
        'groups': [],
    }, merge=True)
    print(f"SUCCESS: Superuser 'admin' created/updated in Firestore.")
except Exception as e:
    print(f"ERROR: {str(e)}")
