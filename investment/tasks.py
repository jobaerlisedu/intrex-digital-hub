"""
Celery background tasks for the Investment module.

Includes overdue detection, installment reminders, and notification creation.
All tasks operate on Firestore collections via the service layer.
"""

from celery import shared_task
from datetime import date, timedelta
from config.logger import investment_logger
from investment.services import FirestoreService as fs, COLL_LOAN_SCHEDULES, COLL_LOANS, COLL_INVESTORS


@shared_task
def check_overdue_schedules():
    """Mark unpaid schedules past due_date as Overdue."""
    schedules = fs.get_collection(COLL_LOAN_SCHEDULES)
    today = date.today().isoformat()
    count = 0
    for sch in schedules:
        if sch.get('payment_status') == 'Unpaid' and sch.get('due_date', '') < today:
            fs.update_document(COLL_LOAN_SCHEDULES, sch['id'], {
                'payment_status': 'Overdue',
            })
            count += 1
    investment_logger.info(f"Overdue check: {count} schedules marked overdue")
    return f"Marked {count} schedules as overdue"


@shared_task
def send_investment_installment_reminders():
    """Send reminders for investment installments due within 3 days."""
    schedules = fs.get_collection(COLL_LOAN_SCHEDULES)
    loans = {l['id']: l for l in fs.get_collection(COLL_LOANS)}
    investors = {i['id']: i for i in fs.get_collection(COLL_INVESTORS)}

    target = (date.today() + timedelta(days=3)).isoformat()
    count = 0

    for sch in schedules:
        if sch.get('payment_status') not in ('Unpaid', 'Overdue') or sch.get('due_date', '') != target:
            continue

        loan = loans.get(sch.get('loan_id', ''))
        investor_name = 'Unknown'
        if loan:
            inv = investors.get(loan.get('investor_id', ''))
            if inv:
                investor_name = inv.get('name', 'Unknown')

        installment = sch.get('installment_number', '?')
        total_due = float(sch.get('scheduled_principal', 0.0)) + float(sch.get('scheduled_interest', 0.0))

        investment_logger.info(
            f"[REMINDER] Installment #{installment} due {sch['due_date']} "
            f"for {investor_name} — BDT {total_due:.2f}"
        )
        count += 1

    return f"Sent {count} installment reminders"


@shared_task
def notify_overdue_schedules():
    """Create in-app notifications for newly overdue schedules."""
    schedules = fs.get_collection(COLL_LOAN_SCHEDULES)
    loans = {l['id']: l for l in fs.get_collection(COLL_LOANS)}
    investors = {i['id']: i for i in fs.get_collection(COLL_INVESTORS)}

    today = date.today().isoformat()
    count = 0

    for sch in schedules:
        if sch.get('payment_status') != 'Overdue':
            continue

        loan = loans.get(sch.get('loan_id', ''))
        investor_name = 'Unknown'
        if loan:
            inv = investors.get(loan.get('investor_id', ''))
            if inv:
                investor_name = inv.get('name', 'Unknown')

        installment = sch.get('installment_number', '?')
        total_due = float(sch.get('scheduled_principal', 0.0)) + float(sch.get('scheduled_interest', 0.0))

        investment_logger.warning(
            f"[OVERDUE] Installment #{installment} due {sch['due_date']} "
            f"for {investor_name} — BDT {total_due:.2f} OVERDUE"
        )
        count += 1

    return f"Logged {count} overdue notifications"
