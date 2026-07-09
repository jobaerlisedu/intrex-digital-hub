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


def sync_all_users_from_firestore():
    from django.contrib.auth.models import User, Group
    from config.firebase import db

    try:
        docs = db.collection('sys_users').stream()
        count = 0
        for doc in docs:
            data = doc.to_dict()
            username = data.get('username') or doc.id
            user, _ = User.objects.update_or_create(
                username=username,
                defaults={
                    'email': data.get('email', ''),
                    'password': data.get('password', ''),
                    'first_name': data.get('first_name', ''),
                    'last_name': data.get('last_name', ''),
                    'is_staff': data.get('is_staff', False),
                    'is_superuser': data.get('is_superuser', False),
                    'is_active': data.get('is_active', True),
                }
            )
            for group_name in data.get('groups', []) or []:
                group, _ = Group.objects.get_or_create(name=group_name)
                user.groups.add(group)
            count += 1
        if count:
            print(f"       Synced {count} user(s) from Firestore to local database.")
    except Exception as e:
        print(f"ERROR syncing users from Firestore: {e}")


def sync_employees_from_firestore():
    """Recreate Person and Employee ORM records from Firestore hrm_employees."""
    from django.contrib.auth.models import User
    from hrm.models import Employee
    from registry.models import Person
    from config.firebase import db

    try:
        docs = db.collection('hrm_employees').stream()
        count = 0
        for doc in docs:
            data = doc.to_dict()
            email = (data.get('email') or '').strip().lower()
            if not email:
                continue
            name = data.get('name', '') or f"{data.get('first_name', '')} {data.get('last_name', '')}"
            name = name.strip()
            first_name = name.split()[0] if name and ' ' in name else (data.get('first_name', name.split()[0] if name else ''))
            last_name = ' '.join(name.split()[1:]) if name and ' ' in name else (data.get('last_name', ''))

            # Find matching User by email (portal user in sys_users)
            user = User.objects.filter(email=email).first()
            if not user:
                continue

            # Create Employee ORM record if missing
            emp_obj = Employee.objects.filter(email=email).first()
            if not emp_obj:
                emp_obj = Employee.objects.create(
                    firestore_id=doc.id,
                    first_name=first_name,
                    last_name=last_name,
                    emp_id=data.get('emp_id', ''),
                    email=email,
                    phone=data.get('phone', ''),
                    is_active=True,
                )

            # Create/update Person record
            person, _ = Person.objects.get_or_create(
                email=email,
                defaults={
                    'display_name': name or email.split('@')[0],
                    'person_type': 'employee',
                    'phone': data.get('phone', ''),
                    'roles': ['employee'],
                    'auth_user': user,
                    'firestore_employee_id': doc.id,
                }
            )
            if not person.auth_user or not person.firestore_employee_id:
                person.auth_user = user
                person.firestore_employee_id = doc.id
                person.save()

            count += 1
        if count:
            print(f"       Synced {count} employee(s) from Firestore to local database.")
    except Exception as e:
        print(f"ERROR syncing employees from Firestore: {e}")


def run_startup():
    from django.core.management import call_command

    print("Django Startup: Running database migrations...")
    call_command('migrate', interactive=False)

    print("Django Startup: Bootstrapping default admin user...")
    create_admin_user()

    print("Django Startup: Syncing all users from Firestore...")
    sync_all_users_from_firestore()

    print("Django Startup: Syncing employees from Firestore...")
    sync_employees_from_firestore()
