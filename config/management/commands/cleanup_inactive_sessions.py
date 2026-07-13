from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from accounts.models import ActiveSession


class Command(BaseCommand):
    help = 'Clean up stale ActiveSession records older than 24 hours'

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(hours=24)
        deleted, _ = ActiveSession.objects.filter(last_activity__lt=cutoff).delete()
        self.stdout.write(f'Cleaned up {deleted} stale sessions')
