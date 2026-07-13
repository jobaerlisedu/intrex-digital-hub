from django.core.management.base import BaseCommand
from django.utils import timezone
import datetime
from training.models import PaymentInstallment


class Command(BaseCommand):
    help = 'Send reminders for installments due in 3 days'

    def handle(self, *args, **options):
        today = datetime.date.today()
        target = today + datetime.timedelta(days=3)
        due_inst = PaymentInstallment.objects.filter(
            due_date=target, status='Pending'
        ).select_related('payment__student')
        count = 0
        for inst in due_inst:
            student_name = getattr(inst.payment.student, 'full_name',
                                   getattr(inst.payment.student, 'fullName', 'Unknown'))
            self.stdout.write(f'Reminder: Installment due for {student_name} - {inst.amount}')
            count += 1
        self.stdout.write(f'Sent {count} installment reminders')
