from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from config.logger import accounts_logger


def sync_user_to_firestore(user):
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
        accounts_logger.error(f"Failed to sync user '{user.username}' to Firestore: {e}")
        return False


class Command(BaseCommand):
    help = 'Backfill all existing Django users to Firestore sys_users collection'

    def handle(self, *args, **options):
        users = User.objects.all().order_by('date_joined')
        total = users.count()
        synced = 0
        failed = 0

        self.stdout.write(f"Found {total} user(s) to sync...")

        for user in users:
            if sync_user_to_firestore(user):
                synced += 1
                self.stdout.write(f"  ✓ {user.username}")
            else:
                failed += 1
                self.stdout.write(self.style.ERROR(f"  ✗ {user.username}"))

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. {synced} synced, {failed} failed out of {total} total."
        ))
