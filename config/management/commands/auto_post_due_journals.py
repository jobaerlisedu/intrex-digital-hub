from django.core.management.base import BaseCommand
from billing.models import JournalEntry


class Command(BaseCommand):
    help = 'Auto-post draft journal entries'

    def handle(self, *args, **options):
        count = JournalEntry.objects.filter(status='Draft').update(status='Posted')
        self.stdout.write(f'Auto-posted {count} journals')
