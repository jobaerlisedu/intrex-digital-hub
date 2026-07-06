from django.core.management.base import BaseCommand
from workflow.services import initialize_standard_workflows


class Command(BaseCommand):
    help = 'Initialize standard workflow definitions for all modules'

    def handle(self, *args, **options):
        initialize_standard_workflows()
        self.stdout.write(self.style.SUCCESS('Standard workflows initialized successfully.'))
