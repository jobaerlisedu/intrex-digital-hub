from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from config.logger import accounts_logger


def push_user_to_firestore(user):
    try:
        from config.firebase import db
        data = {
            'username': user.username,
            'email': user.email,
            'password': user.password,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'is_active': user.is_active,
            'groups': list(user.groups.values_list('name', flat=True)),
        }
        db.collection('sys_users').document(user.username).set(data)
        return True
    except Exception as e:
        accounts_logger.error(f"Failed to push user '{user.username}' to Firestore: {e}")
        return False


def pull_user_from_firestore(doc):
    try:
        from config.firebase import db
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
        return True
    except Exception as e:
        accounts_logger.error(f"Failed to pull user '{doc.id}' from Firestore: {e}")
        return False


class Command(BaseCommand):
    help = 'Sync users between Django SQLite and Firestore'

    def add_arguments(self, parser):
        parser.add_argument(
            '--direction', '-d',
            choices=['push', 'pull', 'both'],
            default='push',
            help='Sync direction: push (SQLite→Firestore), pull (Firestore→SQLite), or both'
        )

    def handle(self, *args, **options):
        direction = options['direction']
        result = {'pushed': 0, 'push_failed': 0, 'pulled': 0, 'pull_failed': 0}

        if direction in ('push', 'both'):
            from config.firebase import db
            users = User.objects.all().order_by('date_joined')
            self.stdout.write(f"Pushing {users.count()} user(s) to Firestore...")
            for user in users:
                if push_user_to_firestore(user):
                    result['pushed'] += 1
                    self.stdout.write(f"  → {user.username}")
                else:
                    result['push_failed'] += 1
                    self.stdout.write(self.style.ERROR(f"  ✗ {user.username}"))

        if direction in ('pull', 'both'):
            from config.firebase import db
            docs = db.collection('sys_users').stream()
            doc_list = list(docs)
            self.stdout.write(f"Pulling {len(doc_list)} user(s) from Firestore...")
            for doc in doc_list:
                if pull_user_from_firestore(doc):
                    result['pulled'] += 1
                    self.stdout.write(f"  ← {doc.id}")
                else:
                    result['pull_failed'] += 1
                    self.stdout.write(self.style.ERROR(f"  ✗ {doc.id}"))

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. Pushed {result['pushed']} ({result['push_failed']} failed), "
            f"Pulled {result['pulled']} ({result['pull_failed']} failed)."
        ))
