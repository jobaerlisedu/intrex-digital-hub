"""
Celery background tasks for the Investment module.
"""

from celery import shared_task
from datetime import date, timedelta
from config.logger import investment_logger
from investment.models import (
    LoanSchedule, Loan, Investor, InvestorHolding,
    NavHistory, FeeAccrual,
)
from investment.services import money_add, money_to_float, money_to_str, ComplianceService


@shared_task
def check_overdue_schedules():
    """Mark unpaid schedules past due_date as Overdue."""
    schedules = LoanSchedule.objects.filter(payment_status='Unpaid', is_active=True)
    today = date.today()
    count = 0
    for sch in schedules:
        if sch.due_date and sch.due_date < today:
            sch.payment_status = 'Overdue'
            sch.save()
            count += 1
    investment_logger.info(f"Overdue check: {count} schedules marked overdue")
    return f"Marked {count} schedules as overdue"


@shared_task
def send_investment_installment_reminders():
    """Send reminders for investment installments due within 3 days."""
    target = (date.today() + timedelta(days=3))
    schedules = LoanSchedule.objects.filter(due_date=target, is_active=True).select_related('loan__investor')

    count = 0
    for sch in schedules:
        if sch.payment_status not in ('Unpaid', 'Overdue'):
            continue

        investor_name = sch.loan.investor.name if sch.loan and sch.loan.investor else 'Unknown'
        installment = sch.installment_number
        total_due = float(sch.scheduled_principal) + float(sch.scheduled_interest)

        investment_logger.info(
            f"[REMINDER] Installment #{installment} due {sch.due_date} "
            f"for {investor_name} — {money_to_str(total_due)}"
        )
        count += 1

    return f"Sent {count} installment reminders"


@shared_task
def notify_overdue_schedules():
    """Create in-app notifications for newly overdue schedules."""
    schedules = LoanSchedule.objects.filter(payment_status='Overdue', is_active=True).select_related('loan__investor')
    count = 0

    for sch in schedules:
        investor_name = sch.loan.investor.name if sch.loan and sch.loan.investor else 'Unknown'
        installment = sch.installment_number
        total_due = float(sch.scheduled_principal) + float(sch.scheduled_interest)

        investment_logger.warning(
            f"[OVERDUE] Installment #{installment} due {sch.due_date} "
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
    """End-of-month fee accrual (management + performance)."""
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
            FeeAccrual.objects.create(
                accrual_date=nav_date,
                fee_type='performance',
                amount=money_to_float(perf_fee),
                nav_before_fee=nav_before,
                nav_after_fee=nav_after,
            )

    investment_logger.info(f"Monthly fee accrual complete for {nav_date}")
    return f"Monthly fees accrued for {nav_date}"


@shared_task
def check_kyc_expiry():
    """Flag investors with expired or soon-to-expire KYC."""
    report = ComplianceService.kyc_compliance_report()
    today = date.today()

    expired_count = 0
    soon_count = 0

    for entry in report:
        inv_id = entry['investor_id']
        if entry['is_expired']:
            Investor.objects.filter(pk=inv_id).update(is_active=False)
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

    today = date.today()
    period = today.strftime('%Y-%m')
    investors = Investor.objects.filter(is_active=True)

    count = 0
    for inv in investors:
        inv_id = str(inv.id)
        try:
            pdf_bytes = PdfStatementService.generate_investor_statement(inv_id, period)
            investment_logger.info(f"[STATEMENT] Generated statement for {inv.name} — {len(pdf_bytes)} bytes")
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
