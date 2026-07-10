import os, sys, time

_SYNC_SENTINEL = None

LAST_SYNC_FILE = None

COOLDOWN_SECONDS = 300

def _should_sync():
    global LAST_SYNC_FILE
    if LAST_SYNC_FILE is None:
        LAST_SYNC_FILE = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', '.last_firestore_sync'
        )
    if os.path.exists(LAST_SYNC_FILE):
        try:
            mtime = os.path.getmtime(LAST_SYNC_FILE)
            if time.time() - mtime < COOLDOWN_SECONDS:
                return False
        except OSError:
            pass
    return True


def _touch_sync():
    if LAST_SYNC_FILE:
        try:
            with open(LAST_SYNC_FILE, 'w') as f:
                f.write(str(time.time()))
        except OSError:
            pass


def _check_quota(e):
    msg = str(e)
    if '429' in msg or 'Quota' in msg or 'RESOURCE_EXHAUSTED' in msg:
        _touch_sync()
        return True
    return False


def create_admin_user():
    from django.conf import settings
    from django.contrib.auth.hashers import make_password
    from django.contrib.auth.models import User

    if User.objects.filter(username='admin').exists():
        return

    if not _should_sync():
        return

    try:
        from config.firebase import db
        admin_ref = db.collection('sys_users').document('admin')
        admin_doc = admin_ref.get()

        if admin_doc.exists:
            data = admin_doc.to_dict()
            password_hash = data.get('password', '')
            email = data.get('email', '')
        else:
            admin_password = settings.ADMIN_PASSWORD
            if not admin_password:
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

        User.objects.update_or_create(
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
        _touch_sync()
    except Exception as e:
        _check_quota(e)


def sync_all_users_from_firestore():
    if User.objects.exclude(username='admin').exists():
        return

    if not _should_sync():
        return

    try:
        from config.firebase import db
        from django.contrib.auth.models import User, Group
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
            _touch_sync()
    except Exception as e:
        _check_quota(e)


def sync_employees_from_firestore():
    if not _should_sync():
        return

    try:
        from config.firebase import db
        from django.contrib.auth.models import User
        from hrm.models import Employee
        from registry.models import Person
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

            user = User.objects.filter(email=email).first()
            if not user:
                continue

            Employee.objects.get_or_create(
                email=email,
                defaults={
                    'firestore_id': doc.id,
                    'first_name': first_name,
                    'last_name': last_name,
                    'emp_id': data.get('emp_id', ''),
                    'phone': data.get('phone', ''),
                    'is_active': True,
                }
            )

            Person.objects.get_or_create(
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
            count += 1
        if count:
            _touch_sync()
    except Exception as e:
        _check_quota(e)


def run_startup():
    from django.core.management import call_command

    call_command('migrate', interactive=False)

    create_admin_user()
    sync_all_users_from_firestore()
    sync_employees_from_firestore()
