import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from config.firebase import db
from django.contrib.auth.models import User

try:
    from django.contrib.auth.hashers import make_password

    admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
    admin_email = os.environ.get('ADMIN_EMAIL', 'admin@intrex.com')
    admin_hash = make_password(admin_password)

    user, created = User.objects.get_or_create(username='admin', defaults={
        'email': admin_email,
        'is_staff': True,
        'is_superuser': True,
        'is_active': True,
    })
    if not created:
        user.email = admin_email
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
    user._syncing = True
    user.password = admin_hash
    user.save()

    print(f"{'Created' if created else 'Updated'} superuser 'admin' in Django.")

    # Push the correct hash to Firestore (non-sensitive profile only)
    db.collection('sys_users').document('admin').set({
        'username': 'admin',
        'email': admin_email,
        'first_name': 'Super',
        'last_name': 'Admin',
        'is_staff': True,
        'is_superuser': True,
        'is_active': True,
        'groups': [],
    }, merge=True)
    print("Synced admin profile to Firestore (no password stored).")
except Exception as e:
    print(f"ERROR: {str(e)}")
