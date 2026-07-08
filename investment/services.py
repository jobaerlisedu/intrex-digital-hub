from django.db import transaction
from .models import Loan, LoanSchedule, PLLedger
from datetime import date


def create_loan_schedule(loan):
    schedule = []
    monthly_principal = loan.principal_amount / loan.tenure_months
    monthly_interest_rate = loan.interest_rate / 100 / 12
    balance = loan.principal_amount

    for i in range(1, loan.tenure_months + 1):
        interest = balance * monthly_interest_rate
        principal = monthly_principal
        balance -= principal
        schedule.append(LoanSchedule.objects.create(
            loan=loan,
            installment_number=i,
            due_date=date(loan.disbursement_date.year + (loan.disbursement_date.month + i - 1) // 12,
                          (loan.disbursement_date.month + i - 1) % 12 + 1, 1),
            scheduled_principal=round(principal, 2),
            scheduled_interest=round(interest, 2),
            paid_amount=0,
            payment_status='Pending',
        ))
    return schedule


def calculate_pl(month_str, user):
    with transaction.atomic():
        pl, _ = PLLedger.objects.get_or_create(
            month=month_str,
            defaults={'created_by': user},
        )
        pl.net_profit = pl.revenue - pl.opex - pl.interest_expense
        pl.save()
    return pl
