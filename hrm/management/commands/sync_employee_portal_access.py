from django.core.management.base import BaseCommand
from config.firebase import db
from config.services.integration_service import IntegrationService
from config.logger import hrm_logger


class Command(BaseCommand):
    help = 'Sync all Firestore employees to registry, creating Person/auth_user records where missing'

    def handle(self, *args, **options):
        try:
            docs = db.collection('hrm_employees').stream()
        except Exception as e:
            self.stderr.write(f"Error fetching employees from Firestore: {e}")
            return

        synced = 0
        skipped = 0
        failed = 0

        for doc in docs:
            emp = doc.to_dict()
            emp['id'] = doc.id
            email = emp.get('email', '')

            if not email:
                self.stdout.write(f"  SKIP  {emp.get('emp_id', '?')} — no email")
                skipped += 1
                continue

            from registry.models import Person
            existing = Person.objects.filter(
                auth_user__isnull=False,
                firestore_employee_id=doc.id
            ).first()

            if existing:
                self.stdout.write(f"  OK    {emp.get('emp_id', '?')} — {existing.auth_user.username}")
                skipped += 1
                continue

            try:
                IntegrationService.employee_to_user_registry(emp)
                person = Person.objects.filter(firestore_employee_id=doc.id).first()
                if person and person.auth_user:
                    self.stdout.write(self.style.SUCCESS(
                        f"  SYNC  {emp.get('emp_id', '?')} → {person.auth_user.username}"
                    ))
                    synced += 1
                else:
                    self.stdout.write(self.style.WARNING(
                        f"  PART  {emp.get('emp_id', '?')} — Person created but no auth_user"
                    ))
                    synced += 1
            except Exception as e:
                self.stderr.write(f"  FAIL  {emp.get('emp_id', '?')} — {e}")
                failed += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. Synced: {synced}, Skipped: {skipped}, Failed: {failed}"
        ))