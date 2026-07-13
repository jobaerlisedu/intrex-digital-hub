"""
PDF Statement Generation Service

Uses ReportLab to generate investor statements and portfolio reports.
"""
from io import BytesIO
from datetime import date, datetime
import calendar

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

from investment.models import (
    Investor, Transaction, InvestorHolding,
    NavHistory, FeeAccrual, Loan,
)
from investment.services import (
    PerformanceService,
    ComplianceService,
    NavService,
    money_to_float,
    money_to_str,
)

# Colors
ACCENT = HexColor('#0f766e')
DARK = HexColor('#1e293b')
GRAY = HexColor('#64748b')
LIGHT_GRAY = HexColor('#f1f5f9')
GREEN = HexColor('#10b981')
RED = HexColor('#ef4444')

styles = getSampleStyleSheet()
styles.add(ParagraphStyle('Title2', parent=styles['Title'], fontSize=18, textColor=ACCENT, spaceAfter=4))
styles.add(ParagraphStyle('SubTitle', parent=styles['Normal'], fontSize=10, textColor=GRAY, spaceAfter=16))
styles.add(ParagraphStyle('SectionHead', parent=styles['Heading2'], fontSize=13, textColor=DARK, spaceBefore=16, spaceAfter=8))
styles.add(ParagraphStyle('CellNormal', parent=styles['Normal'], fontSize=9, textColor=DARK))
styles.add(ParagraphStyle('CellRight', parent=styles['Normal'], fontSize=9, textColor=DARK, alignment=TA_RIGHT))
styles.add(ParagraphStyle('CellCenter', parent=styles['Normal'], fontSize=9, textColor=DARK, alignment=TA_CENTER))
styles.add(ParagraphStyle('SmallText', parent=styles['Normal'], fontSize=8, textColor=GRAY))
styles.add(ParagraphStyle('Disclaimer', parent=styles['Normal'], fontSize=7, textColor=GRAY, alignment=TA_CENTER))
styles.add(ParagraphStyle('KpiValue', parent=styles['Normal'], fontSize=14, textColor=DARK, spaceAfter=2))
styles.add(ParagraphStyle('KpiLabel', parent=styles['Normal'], fontSize=7, textColor=GRAY, spaceAfter=8))


def _build_statement_doc(investor: Investor, period: str) -> list:
    """Build the story (list of flowables) for an investor statement."""
    inv_id = str(investor.id)
    inv_name = investor.name
    inv_code = investor.investor_code or ''

    holdings = InvestorHolding.objects.filter(investor=investor, is_active=True)

    year, month = map(int, period.split('-'))
    _, last_day = calendar.monthrange(year, month)
    period_start = date(year, month, 1)
    period_end = date(year, month, last_day)

    transactions = Transaction.objects.filter(
        investor=investor, status='Cleared', is_active=True,
        value_date__gte=period_start, value_date__lte=period_end,
    ).order_by('value_date')

    nav_history = list(NavHistory.objects.filter(is_active=True).order_by('nav_date'))
    fee_accruals = FeeAccrual.objects.filter(
        is_active=True,
        accrual_date__gte=period_start, accrual_date__lte=period_end,
    )

    elements = []

    # Header
    elements.append(Paragraph('Intrex Digital Hub', styles['Title2']))
    elements.append(Paragraph(f'Investor Statement — {period}', styles['SubTitle']))
    elements.append(HRFlowable(width='100%', color=ACCENT, thickness=1.5))
    elements.append(Spacer(1, 8))

    # Investor info
    info_data = [
        [Paragraph('Investor', styles['CellNormal']), Paragraph(inv_name, styles['CellNormal']),
         Paragraph('Code', styles['CellNormal']), Paragraph(inv_code, styles['CellNormal'])],
        [Paragraph('Date', styles['CellNormal']), Paragraph(date.today().isoformat(), styles['CellNormal']),
         Paragraph('Period', styles['CellNormal']), Paragraph(period, styles['CellNormal'])],
    ]
    info_table = Table(info_data, colWidths=[50, 150, 50, 150])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT_GRAY),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, GRAY),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 16))

    # Portfolio Summary
    elements.append(Paragraph('1. Portfolio Summary', styles['SectionHead']))
    total_invested = sum(float(h.total_invested) for h in holdings)
    total_value = sum(float(h.current_value) for h in holdings)
    total_pl = sum(float(h.unrealized_pl) for h in holdings)
    return_pct = round((total_pl / total_invested) * 100, 2) if total_invested > 0 else 0.0

    summary_data = [
        [Paragraph('Total Invested', styles['CellNormal']), Paragraph(f'BDT {total_invested:,.2f}', styles['CellRight'])],
        [Paragraph('Current Value', styles['CellNormal']), Paragraph(f'BDT {total_value:,.2f}', styles['CellRight'])],
        [Paragraph('Unrealized P&L', styles['CellNormal']), Paragraph(f'BDT {total_pl:,.2f}', styles['CellRight'])],
        [Paragraph('Return %', styles['CellNormal']), Paragraph(f'{return_pct}%', styles['CellRight'])],
    ]
    summary_table = Table(summary_data, colWidths=[280, 280])
    summary_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, GRAY),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 12))

    # Holdings Detail
    if holdings.exists():
        elements.append(Paragraph('2. Holdings Detail', styles['SectionHead']))
        hdr = [Paragraph('Units Held', styles['CellCenter']), Paragraph('Avg Cost', styles['CellCenter']),
               Paragraph('Invested', styles['CellCenter']), Paragraph('Current Value', styles['CellCenter']),
               Paragraph('P&L', styles['CellCenter'])]
        rows = [hdr]
        for h in holdings:
            rows.append([
                Paragraph(str(h.units_held), styles['CellCenter']),
                Paragraph(f'BDT {float(h.avg_cost_per_unit):,.4f}', styles['CellRight']),
                Paragraph(f'BDT {float(h.total_invested):,.2f}', styles['CellRight']),
                Paragraph(f'BDT {float(h.current_value):,.2f}', styles['CellRight']),
                Paragraph(f'BDT {float(h.unrealized_pl):,.2f}', styles['CellRight']),
            ])
        h_table = Table(rows, colWidths=[80, 90, 110, 110, 110])
        h_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('GRID', (0, 0), (-1, -1), 0.5, GRAY),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT_GRAY]),
        ]))
        elements.append(h_table)
        elements.append(Spacer(1, 12))

    # Transaction History
    if transactions.exists():
        elements.append(Paragraph(f'3. Transaction History — {period}', styles['SectionHead']))
        tx_hdr = [Paragraph('Date', styles['CellCenter']), Paragraph('Type', styles['CellCenter']),
                  Paragraph('Amount', styles['CellCenter']), Paragraph('Method', styles['CellCenter'])]
        tx_rows = [tx_hdr]
        for t in transactions:
            tx_rows.append([
                Paragraph(t.value_date.isoformat() if t.value_date else '', styles['CellCenter']),
                Paragraph(t.transaction_type, styles['CellCenter']),
                Paragraph(f'BDT {float(t.amount):,.2f}', styles['CellRight']),
                Paragraph(t.payment_method, styles['CellCenter']),
            ])
        tx_table = Table(tx_rows, colWidths=[90, 150, 150, 150])
        tx_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('GRID', (0, 0), (-1, -1), 0.5, GRAY),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT_GRAY]),
        ]))
        elements.append(tx_table)
        elements.append(Spacer(1, 12))

    # Fee Summary
    if fee_accruals.exists():
        elements.append(Paragraph('4. Fee Summary', styles['SectionHead']))
        fee_hdr = [Paragraph('Date', styles['CellCenter']), Paragraph('Type', styles['CellCenter']),
                   Paragraph('Amount', styles['CellCenter']), Paragraph('Status', styles['CellCenter'])]
        fee_rows = [fee_hdr]
        for f in fee_accruals:
            fee_rows.append([
                Paragraph(f.accrual_date.isoformat() if f.accrual_date else '', styles['CellCenter']),
                Paragraph(f.fee_type.capitalize(), styles['CellCenter']),
                Paragraph(f'BDT {float(f.amount):,.2f}', styles['CellRight']),
                Paragraph('Settled' if f.is_settled else 'Pending', styles['CellCenter']),
            ])
        fee_table = Table(fee_rows, colWidths=[100, 120, 160, 160])
        fee_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('GRID', (0, 0), (-1, -1), 0.5, GRAY),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT_GRAY]),
        ]))
        elements.append(fee_table)
        elements.append(Spacer(1, 12))

    # Performance Metrics
    elements.append(Paragraph('5. Performance Metrics (Since Inception)', styles['SectionHead']))
    returns = []
    for i in range(1, len(nav_history)):
        prev_nav = float(nav_history[i - 1].nav_per_unit)
        curr_nav = float(nav_history[i].nav_per_unit)
        if prev_nav > 0:
            returns.append((curr_nav - prev_nav) / prev_nav)

    def nav_to_dict(n):
        return {'nav_per_unit': str(n.nav_per_unit), 'nav_date': n.nav_date.isoformat() if n.nav_date else ''}
    nav_dicts = [nav_to_dict(n) for n in nav_history]

    perf_data = [
        [Paragraph('Metric', styles['CellNormal']), Paragraph('Value', styles['CellNormal'])],
        [Paragraph('TWRR (Since Inception)', styles['CellNormal']),
         Paragraph(f'{round(PerformanceService.time_weighted_return(nav_dicts) * 100, 4)}%', styles['CellRight'])],
        [Paragraph('Sharpe Ratio', styles['CellNormal']),
         Paragraph(f'{PerformanceService.sharpe_ratio(returns)}', styles['CellRight']) if returns else Paragraph('N/A', styles['CellRight'])],
        [Paragraph('Max Drawdown', styles['CellNormal']),
         Paragraph(f'{PerformanceService.max_drawdown(nav_dicts)["max_drawdown_pct"]}%', styles['CellRight'])],
        [Paragraph('Volatility (Annualized)', styles['CellNormal']),
         Paragraph(f'{round(PerformanceService.volatility(returns) * 100, 4)}%', styles['CellRight']) if len(returns) >= 2 else Paragraph('N/A', styles['CellRight'])],
    ]
    perf_table = Table(perf_data, colWidths=[280, 280])
    perf_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('GRID', (0, 0), (-1, -1), 0.5, GRAY),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT_GRAY]),
    ]))
    elements.append(perf_table)
    elements.append(Spacer(1, 24))

    # Disclaimer
    elements.append(HRFlowable(width='100%', color=GRAY, thickness=0.5))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(
        'This statement is auto-generated and does not constitute a legally binding document. '
        'All values are in BDT unless otherwise stated. Past performance is not indicative of future results. '
        'For any discrepancies, please contact your relationship manager.',
        styles['Disclaimer']
    ))

    return elements


class PdfStatementService:
    """Generate PDF statements for investors."""

    @staticmethod
    def generate_investor_statement(investor_id: str, period: str) -> bytes:
        """Generate a PDF statement for an investor for a given period (YYYY-MM)."""
        try:
            investor = Investor.objects.get(pk=investor_id)
        except Investor.DoesNotExist:
            raise ValueError(f'Investor {investor_id} not found')

        buf = BytesIO()
        doc = SimpleDocTemplate(
            buf, pagesize=A4,
            leftMargin=20 * mm, rightMargin=20 * mm,
            topMargin=20 * mm, bottomMargin=20 * mm,
        )
        story = _build_statement_doc(investor, period)
        doc.build(story)
        buf.seek(0)
        return buf.getvalue()

    @staticmethod
    def generate_portfolio_report(period: str) -> bytes:
        """Generate a firm-wide portfolio report for a given period."""
        investors = Investor.objects.filter(is_active=True)
        nav_history = list(NavHistory.objects.filter(is_active=True).order_by('nav_date'))

        buf = BytesIO()
        doc = SimpleDocTemplate(
            buf, pagesize=A4,
            leftMargin=20 * mm, rightMargin=20 * mm,
            topMargin=20 * mm, bottomMargin=20 * mm,
        )
        elements = []

        elements.append(Paragraph('Intrex Digital Hub', styles['Title2']))
        elements.append(Paragraph(f'Portfolio Report — {period}', styles['SubTitle']))
        elements.append(HRFlowable(width='100%', color=ACCENT, thickness=1.5))
        elements.append(Spacer(1, 12))

        elements.append(Paragraph('1. Portfolio Summary', styles['SectionHead']))
        total_aum = float(nav_history[-1].total_aum) if nav_history else 0.0
        total_investors = investors.count()
        total_holdings = InvestorHolding.objects.filter(is_active=True).count()

        summary_data = [
            [Paragraph('Metric', styles['CellNormal']), Paragraph('Value', styles['CellNormal'])],
            [Paragraph('Total AUM', styles['CellNormal']), Paragraph(f'BDT {total_aum:,.2f}', styles['CellRight'])],
            [Paragraph('Active Investors', styles['CellNormal']), Paragraph(str(total_investors), styles['CellRight'])],
            [Paragraph('Total Holdings', styles['CellNormal']), Paragraph(str(total_holdings), styles['CellRight'])],
        ]

        def nav_to_dict(n):
            return {'nav_per_unit': str(n.nav_per_unit), 'nav_date': n.nav_date.isoformat() if n.nav_date else ''}
        nav_dicts = [nav_to_dict(n) for n in nav_history]

        if len(nav_history) >= 2:
            twrr = PerformanceService.time_weighted_return(nav_dicts)
            summary_data.append([
                Paragraph('Portfolio TWRR', styles['CellNormal']),
                Paragraph(f'{round(twrr * 100, 4)}%', styles['CellRight']),
            ])

        s_table = Table(summary_data, colWidths=[280, 280])
        s_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('GRID', (0, 0), (-1, -1), 0.5, GRAY),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT_GRAY]),
        ]))
        elements.append(s_table)
        elements.append(Spacer(1, 16))

        elements.append(Paragraph('2. Concentration Analysis', styles['SectionHead']))
        concentrations = ComplianceService.all_investor_concentrations()

        conc_hdr = [Paragraph('Investor', styles['CellCenter']), Paragraph('Holding Value', styles['CellCenter']),
                    Paragraph('Concentration %', styles['CellCenter']), Paragraph('Status', styles['CellCenter'])]
        conc_rows = [conc_hdr]
        for c in concentrations[:15]:
            conc_rows.append([
                Paragraph(c['investor_name'], styles['CellNormal']),
                Paragraph(f'BDT {money_to_float(c["holding_value"]):,.2f}', styles['CellRight']),
                Paragraph(f'{c["concentration_pct"]:.2f}%', styles['CellRight']),
                Paragraph('<font color="red">BREACH</font>' if c['breached'] else 'OK', styles['CellCenter']),
            ])
        c_table = Table(conc_rows, colWidths=[120, 140, 120, 120])
        c_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('GRID', (0, 0), (-1, -1), 0.5, GRAY),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT_GRAY]),
        ]))
        elements.append(c_table)
        elements.append(Spacer(1, 24))

        elements.append(HRFlowable(width='100%', color=GRAY, thickness=0.5))
        elements.append(Spacer(1, 8))
        elements.append(Paragraph(
            'This report is auto-generated for internal use. All values in BDT. '
            'Past performance is not indicative of future results.',
            styles['Disclaimer']
        ))

        doc.build(elements)
        buf.seek(0)
        return buf.getvalue()
