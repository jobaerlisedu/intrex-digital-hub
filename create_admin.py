import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from config.firebase import db
from django.contrib.auth.models import User

try:
    # Check if 'admin' already exists in Firestore
    admin_doc = db.collection('users').document('admin').get()
    if admin_doc.exists:
        print("INFO: 'admin' superuser already exists in Firestore. Relying on Firestore sync.")
    elif not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        print("SUCCESS: Default superuser 'admin' created.")
    else:
        print("INFO: Local 'admin' superuser already exists.")
except Exception as e:
    print(f"ERROR: {str(e)}")

# Sync users from Firestore
try:
    from accounts.auth_backend import sync_users_from_firestore
    print("Syncing users from Firestore...")
    sync_users_from_firestore()
    print("SUCCESS: Users synced successfully.")
except Exception as e:
    print(f"ERROR syncing users: {str(e)}")
