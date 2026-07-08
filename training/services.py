from django.db import transaction
from .models import Batch, Registration, Payment


def enroll_student(batch, student_data, payment_data, user):
    with transaction.atomic():
        registration = Registration.objects.create(
            batch=batch,
            course=batch.course,
            full_name=student_data['full_name'],
            email=student_data['email'],
            phone=student_data['phone'],
            created_by=user,
        )
        Payment.objects.create(
            registration=registration,
            total_fee=payment_data['total_fee'],
            amount_paid=payment_data.get('amount_paid', 0),
            due_amount=payment_data['total_fee'] - payment_data.get('amount_paid', 0),
            status='Pending',
            created_by=user,
        )
    return registration


def get_batch_revenue(batch):
    payments = Payment.objects.filter(registration__batch=batch)
    return sum(p.amount_paid for p in payments)
