from django.db import transaction
from .models import ChartOfAccount, JournalEntry, JournalEntryLine, Invoice, InvoiceLine, Payment, TaxCode


def create_invoice(data, lines_data, user):
    with transaction.atomic():
        invoice = Invoice.objects.create(
            client_name=data['client_name'],
            issue_date=data['issue_date'],
            due_date=data['due_date'],
            subtotal=sum(l['quantity'] * l['unit_price'] for l in lines_data),
            status='Draft',
            created_by=user,
        )
        for line in lines_data:
            InvoiceLine.objects.create(
                invoice=invoice,
                description=line['description'],
                quantity=line['quantity'],
                unit_price=line['unit_price'],
                line_total=line['quantity'] * line['unit_price'],
            )
        invoice.grand_total = invoice.subtotal
        invoice.save()
    return invoice


def record_payment(invoice, amount, method, reference, user):
    with transaction.atomic():
        payment = Payment.objects.create(
            invoice=invoice,
            receipt_code=f"RCP-{invoice.invoice_number}",
            payment_date=timezone.now().date(),
            amount=amount,
            payment_method=method,
            bank_reference=reference,
            created_by=user,
        )
        invoice.status = 'Paid'
        invoice.save()
    return payment
