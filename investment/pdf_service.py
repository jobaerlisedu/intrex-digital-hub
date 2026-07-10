"""
PDF Statement Generation Service

Uses ReportLab to generate investor statements and portfolio reports.
"""
from io import BytesIO
from datetime import date, datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

from investment.services import (
    FirestoreService as fs,
    PerformanceService,
    ComplianceService,
    NavService,
    COLL_INVESTORS,
    COLL_INVESTOR_HOLDINGS,
    COLL_TRANSACTIONS,
    COLL_NAV_HISTORY,
    COLL_FEE_ACCRUALS,
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


def _build_statement_doc(investor: dict, period: str) -> list:
    """Build the story (list of flowables) for an investor statement."""
    inv_id = investor['id']
    inv_name = investor.get('name', 'Investor')
    inv_code = investor.get('investor_code', '')

    holdings = [h for h in fs.get_collection(COLL_INVESTOR_HOLDINGS) if h.get('investor_id') == inv_id]
    transactions = [
        t for t in fs.get_collection(COLL_TRANSACTIONS)
        if t.get('investor_id') == inv_id and t.get('status') == 'Cleared'
        and t.get('value_date', '').startswith(period)
    ]
    transactions.sort(key=lambda t: t.get('value_date', ''))

    nav_history = fs.get_collection(COLL_NAV_HISTORY)
    nav_history.sort(key=lambda r: r.get('nav_date', ''))

    fee_accruals = [f for f in fs.get_collection(COLL_FEE_ACCRUALS) if f.get('accrual_date', '').startswith(period)]

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
    total_invested = sum(money_to_float(h.get('total_invested', '0.00')) for h in holdings)
    total_value = sum(money_to_float(h.get('current_value', '0.00')) for h in holdings)
    total_pl = sum(money_to_float(h.get('unrealized_pl', '0.00')) for h in holdings)
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
    if holdings:
        elements.append(Paragraph('2. Holdings Detail', styles['SectionHead']))
        hdr = [Paragraph('Units Held', styles['CellCenter']), Paragraph('Avg Cost', styles['CellCenter']),
               Paragraph('Invested', styles['CellCenter']), Paragraph('Current Value', styles['CellCenter']),
               Paragraph('P&L', styles['CellCenter'])]
        rows = [hdr]
        for h in holdings:
            rows.append([
                Paragraph(h.get('units_held', '0.0000'), styles['CellCenter']),
                Paragraph(f'BDT {money_to_float(h.get("avg_cost_per_unit", "0.0000")):,.4f}', styles['CellRight']),
                Paragraph(f'BDT {money_to_float(h.get("total_invested", "0.00")):,.2f}', styles['CellRight']),
                Paragraph(f'BDT {money_to_float(h.get("current_value", "0.00")):,.2f}', styles['CellRight']),
                Paragraph(f'BDT {money_to_float(h.get("unrealized_pl", "0.00")):,.2f}', styles['CellRight']),
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
    if transactions:
        elements.append(Paragraph(f'3. Transaction History — {period}', styles['SectionHead']))
        tx_hdr = [Paragraph('Date', styles['CellCenter']), Paragraph('Type', styles['CellCenter']),
                  Paragraph('Amount', styles['CellCenter']), Paragraph('Method', styles['CellCenter'])]
        tx_rows = [tx_hdr]
        for t in transactions:
            tx_rows.append([
                Paragraph(t.get('value_date', ''), styles['CellCenter']),
                Paragraph(t.get('transaction_type', ''), styles['CellCenter']),
                Paragraph(f'BDT {money_to_float(t.get("amount", "0.00")):,.2f}', styles['CellRight']),
                Paragraph(t.get('payment_method', ''), styles['CellCenter']),
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
    if fee_accruals:
        elements.append(Paragraph('4. Fee Summary', styles['SectionHead']))
        fee_hdr = [Paragraph('Date', styles['CellCenter']), Paragraph('Type', styles['CellCenter']),
                   Paragraph('Amount', styles['CellCenter']), Paragraph('Status', styles['CellCenter'])]
        fee_rows = [fee_hdr]
        for f in fee_accruals:
            fee_rows.append([
                Paragraph(f.get('accrual_date', ''), styles['CellCenter']),
                Paragraph(f.get('fee_type', '').capitalize(), styles['CellCenter']),
                Paragraph(f'BDT {money_to_float(f.get("amount", "0.00")):,.2f}', styles['CellRight']),
                Paragraph('Settled' if f.get('is_settled') else 'Pending', styles['CellCenter']),
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
        prev_nav = money_to_float(nav_history[i - 1].get('nav_per_unit', '0.0000'))
        curr_nav = money_to_float(nav_history[i].get('nav_per_unit', '0.0000'))
        if prev_nav > 0:
            returns.append((curr_nav - prev_nav) / prev_nav)

    perf_data = [
        [Paragraph('Metric', styles['CellNormal']), Paragraph('Value', styles['CellNormal'])],
        [Paragraph('TWRR (Since Inception)', styles['CellNormal']),
         Paragraph(f'{round(PerformanceService.time_weighted_return(nav_history) * 100, 4)}%', styles['CellRight'])],
        [Paragraph('Sharpe Ratio', styles['CellNormal']),
         Paragraph(f'{PerformanceService.sharpe_ratio(returns)}', styles['CellRight']) if returns else Paragraph('N/A', styles['CellRight'])],
        [Paragraph('Max Drawdown', styles['CellNormal']),
         Paragraph(f'{PerformanceService.max_drawdown(nav_history)["max_drawdown_pct"]}%', styles['CellRight'])],
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
        investor = fs.get_document(COLL_INVESTORS, investor_id)
        if not investor:
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
        investors = fs.get_collection(COLL_INVESTORS)
        nav_history = fs.get_collection(COLL_NAV_HISTORY)
        nav_history.sort(key=lambda r: r.get('nav_date', ''))

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
        total_aum = money_to_float(nav_history[-1].get('total_aum', '0.00')) if nav_history else 0.0
        total_investors = len(investors)
        total_holdings = len(fs.get_collection(COLL_INVESTOR_HOLDINGS))

        summary_data = [
            [Paragraph('Metric', styles['CellNormal']), Paragraph('Value', styles['CellNormal'])],
            [Paragraph('Total AUM', styles['CellNormal']), Paragraph(f'BDT {total_aum:,.2f}', styles['CellRight'])],
            [Paragraph('Active Investors', styles['CellNormal']), Paragraph(str(total_investors), styles['CellRight'])],
            [Paragraph('Total Holdings', styles['CellNormal']), Paragraph(str(total_holdings), styles['CellRight'])],
        ]

        if len(nav_history) >= 2:
            twrr = PerformanceService.time_weighted_return(nav_history)
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
        sectors = ComplianceService.sector_concentration()

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
