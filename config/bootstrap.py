import os


def create_admin_user():
    from config.firebase import db
    from django.contrib.auth.hashers import make_password

    try:
        admin_ref = db.collection('sys_users').document('admin')
        admin_doc = admin_ref.get()

        if admin_doc.exists:
            print("Admin user already exists, skipping creation.")
            return

        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@intrex.com')
        admin_hash = make_password(admin_password)

        admin_ref.set({
            'username': 'admin',
            'email': admin_email,
            'password': admin_hash,
            'first_name': 'Super',
            'last_name': 'Admin',
            'is_staff': True,
            'is_superuser': True,
            'is_active': True,
            'groups': [],
        })
        print(f"SUCCESS: Superuser 'admin' created in Firestore.")
    except Exception as e:
        print(f"ERROR: {str(e)}")


def run_startup():
    from django.core.management import call_command

    print("Django Startup: Running database migrations...")
    call_command('migrate', interactive=False)

    print("Django Startup: Bootstrapping default admin user...")
    create_admin_user()
