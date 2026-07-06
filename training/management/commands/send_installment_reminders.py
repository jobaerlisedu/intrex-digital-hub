from django.core.management.base import BaseCommand
from config.firebase import db
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Sends payment reminders for student installments due in exactly 3 days'

    def handle(self, *args, **options):
        self.stdout.write("Checking for upcoming student installments due in 3 days...")
        try:
            payments_ref = db.collection('trn_payments').stream()
            reminders_sent = 0
            
            # Target date is exactly 3 days from now
            target_date = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')
            self.stdout.write(f"Looking for unpaid installments due on: {target_date}")
            
            for doc in payments_ref:
                pay_data = doc.to_dict() or {}
                installments = pay_data.get('installments', [])
                student_name = pay_data.get('studentName', 'N/A')
                student_email = pay_data.get('email', 'N/A')
                student_id = pay_data.get('studentId', 'N/A')
                
                for idx, inst in enumerate(installments):
                    due_date = inst.get('dueDate')
                    amount = float(inst.get('amount', 0.0))
                    status = inst.get('status', 'Unpaid')
                    
                    if due_date == target_date and status == 'Unpaid':
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"[REMINDER SENT] Student: {student_name} ({student_id}) - "
                                f"Email: {student_email} - Installment #{idx+1} of amount {amount} is due on {due_date}."
                            )
                        )
                        reminders_sent += 1
            
            self.stdout.write(f"Job completed. Total reminders processed: {reminders_sent}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error checking installments: {e}"))
