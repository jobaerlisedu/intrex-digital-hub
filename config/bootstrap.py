def create_admin_user():
    from django.conf import settings
    from config.firebase import db
    from django.contrib.auth.hashers import make_password

    try:
        admin_ref = db.collection('sys_users').document('admin')
        admin_doc = admin_ref.get()

        if admin_doc.exists:
            print("Admin user already exists, skipping creation.")
            return

        admin_password = settings.ADMIN_PASSWORD
        admin_email = settings.ADMIN_EMAIL
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
        print(f"       Username: admin")
        print(f"       Password: {admin_password}")
        print(f"       Email:    {admin_email}")
    except Exception as e:
        print(f"ERROR: {str(e)}")


def run_startup():
    from django.core.management import call_command

    print("Django Startup: Running database migrations...")
    call_command('migrate', interactive=False)

    print("Django Startup: Bootstrapping default admin user...")
    create_admin_user()
