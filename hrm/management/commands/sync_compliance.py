from django.core.management.base import BaseCommand
from hrm.services import (
    sync_document_compliance_reminders,
    check_compliance_overdue_reminders,
    send_compliance_notifications,
)


class Command(BaseCommand):
    help = 'Sync compliance reminders from documents, check overdue, and send notifications'

    def add_arguments(self, parser):
        parser.add_argument('--notify', action='store_true', help='Send notifications for overdue/upcoming reminders')

    def handle(self, *args, **options):
        result = sync_document_compliance_reminders()
        self.stdout.write(self.style.SUCCESS(f"Synced {result['synced']} document reminders"))

        overdue = check_compliance_overdue_reminders()
        self.stdout.write(self.style.WARNING(f"Marked {overdue['marked_overdue']} as overdue"))

        if options['notify']:
            notified = send_compliance_notifications()
            self.stdout.write(self.style.SUCCESS(f"Sent {notified['notifications_sent']} notifications"))
