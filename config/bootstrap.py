def create_admin_user():
    from django.conf import settings
    from config.firebase import db
    from django.contrib.auth.hashers import make_password
    from django.contrib.auth.models import User

    try:
        from config.firebase import db
        admin_ref = db.collection('sys_users').document('admin')
        admin_doc = admin_ref.get()

        if admin_doc.exists:
            data = admin_doc.to_dict()
            password_hash = data.get('password', '')
            email = data.get('email', '')
            print("Admin user exists in Firestore. Syncing to local database...")
        else:
            admin_password = settings.ADMIN_PASSWORD
            if not admin_password:
                print("ERROR: ADMIN_PASSWORD environment variable is not set. Cannot create admin user.")
                return
            admin_email = settings.ADMIN_EMAIL
            password_hash = make_password(admin_password)
            admin_ref.set({
                'username': 'admin',
                'email': admin_email,
                'password': password_hash,
                'first_name': 'Super',
                'last_name': 'Admin',
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
                'groups': [],
            })
            email = admin_email
            print(f"SUCCESS: Superuser 'admin' created in Firestore.")

        user, created = User.objects.update_or_create(
            username='admin',
            defaults={
                'email': email,
                'password': password_hash,
                'first_name': 'Super',
                'last_name': 'Admin',
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
            }
        )
        verb = "Created" if created else "Updated"
        print(f"       {verb} local admin user (id={user.id}).")
        print(f"       Username: admin | Email: {email}")

    except Exception as e:
        print(f"ERROR: {str(e)}")


def run_startup():
    from django.core.management import call_command

    print("Django Startup: Running database migrations...")
    call_command('migrate', interactive=False)

    print("Django Startup: Bootstrapping default admin user...")
    create_admin_user()
