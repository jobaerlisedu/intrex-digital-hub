"""
Celery background tasks for the Investment module.

Includes overdue detection, installment reminders, and notification creation.
All tasks operate on Firestore collections via the service layer.
"""

from celery import shared_task
from datetime import date, timedelta
from config.logger import investment_logger
from investment.services import FirestoreService as fs, money_add, money_to_float, money_to_str, ComplianceService, COLL_LOAN_SCHEDULES, COLL_LOANS, COLL_INVESTORS, COLL_INVESTOR_HOLDINGS, COLL_NAV_HISTORY, COLL_FEE_ACCRUALS


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
        total_due = money_add(sch.get('scheduled_principal'), sch.get('scheduled_interest'))

        investment_logger.info(
            f"[REMINDER] Installment #{installment} due {sch['due_date']} "
            f"for {investor_name} — {money_to_str(total_due)}"
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
        total_due = money_add(sch.get('scheduled_principal'), sch.get('scheduled_interest'))

        investment_logger.warning(
            f"[OVERDUE] Installment #{installment} due {sch['due_date']} "
            f"for {investor_name} — {money_to_str(total_due)} OVERDUE"
        )
        count += 1

    return f"Logged {count} overdue notifications"


@shared_task
def calculate_daily_nav():
    """Run daily NAV calculation and fee accrual."""
    from investment.services import NavService, FeeService
    nav_date = date.today()
    result = NavService.calculate_nav(nav_date)
    FeeService.accrue_management_fee(nav_date)
    investment_logger.info(f"NAV computed: {result['nav_per_unit']} on {nav_date}")
    return f"NAV computed: {result['nav_per_unit']} on {nav_date}"


@shared_task
def accrue_monthly_fees():
    """End-of-month fee accrual (management + performance).

    Runs daily; only performs full accrual on the last calendar day of the month.
    """
    from calendar import monthrange
    from investment.services import NavService, FeeService
    nav_date = date.today()

    is_last_day = nav_date.day == monthrange(nav_date.year, nav_date.month)[1]
    if not is_last_day:
        return f"Skipped — {nav_date} is not the last day of the month"

    result = NavService.calculate_nav(nav_date)
    mgmt = FeeService.accrue_management_fee(nav_date)

    fee_struct = FeeService.get_fee_structure()
    current_nav = NavService.get_current_nav()
    if current_nav:
        perf_fee = FeeService.calculate_performance_fee(
            current_nav=current_nav['nav_per_unit'],
            high_water_mark=fee_struct.get('high_water_mark', '0.0000'),
            total_units=current_nav['total_units'],
            perf_fee_pct=fee_struct.get('performance_fee_pct', '20.00'),
        )
        if money_to_float(perf_fee) > 0:
            nav_before = money_to_float(current_nav['total_aum'])
            nav_after = round(max(nav_before - money_to_float(perf_fee), 0.0), 2)
            fs.create_document(COLL_FEE_ACCRUALS, {
                'accrual_date': nav_date.isoformat(),
                'fee_type': 'performance',
                'amount': perf_fee,
                'nav_before_fee': f'{nav_before:.2f}',
                'nav_after_fee': f'{nav_after:.2f}',
                'is_settled': False,
                'is_active': True,
            })

    investment_logger.info(f"Monthly fee accrual complete for {nav_date}")
    return f"Monthly fees accrued for {nav_date}"


@shared_task
def check_kyc_expiry():
    """Flag investors with expired or soon-to-expire KYC.

    - Marks investors with KYC 'Expired' as is_active=False
    - Logs warning for KYC expiring within 30 days
    """
    from datetime import date, timedelta
    report = ComplianceService.kyc_compliance_report()
    today = date.today()
    thirty_days = today + timedelta(days=30)

    expired_count = 0
    soon_count = 0

    for entry in report:
        inv_id = entry['investor_id']
        if entry['is_expired']:
            fs.update_document(COLL_INVESTORS, inv_id, {'is_active': False, 'updated_at': today.isoformat()})
            expired_count += 1
            investment_logger.warning(f"[KYC EXPIRED] {entry['investor_name']} ({inv_id}) — set to inactive")
        elif entry['expires_soon']:
            soon_count += 1
            investment_logger.warning(f"[KYC EXPIRING] {entry['investor_name']} ({inv_id}) — expires {entry.get('kyc_expiry_date', 'unknown')}")

    return f"KYC check: {expired_count} expired (deactivated), {soon_count} expiring within 30 days"


@shared_task
def check_concentration_limits():
    """Alert if any investor exceeds concentration threshold (default 25%)."""
    concentrations = ComplianceService.all_investor_concentrations()
    breached = [c for c in concentrations if c['breached']]

    for c in breached:
        investment_logger.warning(
            f"[CONCENTRATION BREACH] {c['investor_name']} ({c['investor_id']}) "
            f"at {c['concentration_pct']:.2f}% exceeds {c['threshold_pct']:.0f}% threshold"
        )

    return f"Concentration check: {len(concentrations)} investors checked, {len(breached)} breaches"


@shared_task
def dispatch_monthly_statements():
    """Generate and log monthly statements for all active investors."""
    from investment.pdf_service import PdfStatementService
    from datetime import date

    today = date.today()
    period = today.strftime('%Y-%m')
    investors = fs.get_collection(COLL_INVESTORS)
    active = [inv for inv in investors if inv.get('is_active', True)]

    count = 0
    for inv in active:
        inv_id = inv.get('id', '')
        if not inv_id:
            continue
        try:
            pdf_bytes = PdfStatementService.generate_investor_statement(inv_id, period)
            # In production, email this as attachment; for now, log generation
            investment_logger.info(f"[STATEMENT] Generated statement for {inv.get('name', inv_id)} — {len(pdf_bytes)} bytes")
            count += 1
        except Exception as e:
            investment_logger.error(f"[STATEMENT] Failed for {inv_id}: {e}")

    return f"Generated {count} monthly statements for {period}"


@shared_task
def dispatch_weekly_performance_summary():
    """Log weekly performance summary (for email dispatch in production)."""
    from investment.reports import ReportService
    pm = ReportService.performance_metrics()
    compliance = ReportService.compliance_overview()

    investment_logger.info(
        f"[WEEKLY SUMMARY] TWRR={pm.get('twrr')}% "
        f"Sharpe={pm.get('sharpe_ratio')} "
        f"MaxDD={pm.get('max_drawdown_pct')}% "
        f"Breaches={compliance.get('breach_count', 0)}"
    )
    return f"Weekly performance summary logged"
