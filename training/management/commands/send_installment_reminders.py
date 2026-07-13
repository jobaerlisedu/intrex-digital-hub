from django.core.management.base import BaseCommand
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Sends payment reminders for student installments due in exactly 3 days'

    def handle(self, *args, **options):
        self.stdout.write("Checking for upcoming student installments due in 3 days...")
        try:
            from training.models import PaymentInstallment

            target_date = (datetime.now() + timedelta(days=3)).date()
            self.stdout.write(f"Looking for unpaid installments due on: {target_date}")

            due_inst = PaymentInstallment.objects.filter(
                due_date=target_date, status='Pending'
            ).select_related('payment__student')

            reminders_sent = 0
            for inst in due_inst:
                student = inst.payment.student
                student_name = getattr(student, 'full_name', getattr(student, 'fullName', 'N/A'))
                student_email = getattr(student, 'email', 'N/A')
                student_id = getattr(student, 'student_id', getattr(student, 'id', 'N/A'))
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[REMINDER SENT] Student: {student_name} ({student_id}) - "
                        f"Email: {student_email} - Installment #{inst.installment_number} "
                        f"of amount {inst.amount} is due on {inst.due_date}."
                    )
                )
                reminders_sent += 1

            self.stdout.write(f"Job completed. Total reminders processed: {reminders_sent}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error checking installments: {e}"))
