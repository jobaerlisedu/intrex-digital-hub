from django.core.management.base import BaseCommand
from config.bootstrap import run_startup


class Command(BaseCommand):
    help = 'Run production startup tasks: migrate, create admin, init workflows, init event subscribers'

    def handle(self, *args, **options):
        run_startup()
        self.stdout.write(self.style.SUCCESS('Startup complete'))
