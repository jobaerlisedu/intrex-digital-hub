"""
Investment Analytics & Reporting Service

Provides data aggregation, report generation, and CSV export
for the investment module. All data sourced from Firestore.
"""

import csv
import json
from datetime import datetime, date
from decimal import Decimal
from collections import defaultdict
from django.http import HttpResponse

from investment.services import (
    FirestoreService as fs,
    COLL_INVESTORS,
    COLL_TRANSACTIONS,
    COLL_LOANS,
    COLL_LOAN_SCHEDULES,
    COLL_OUTBOUND,
    COLL_INSTRUMENTS,
    COLL_PL_LEDGER,
)


class ReportService:
    """Static report generators returning serializable dicts."""

    # ── Capital Overview ─────────────────────────────────────────

    @staticmethod
    def capital_overview():
        investors = fs.get_collection(COLL_INVESTORS)
        transactions = fs.get_collection(COLL_TRANSACTIONS)
        loans = fs.get_collection(COLL_LOANS)
        outbound = fs.get_collection(COLL_OUTBOUND)
        schedules = fs.get_collection(COLL_LOAN_SCHEDULES)

        total_inflow = 0.0
        total_outflow = 0.0
        for tx in transactions:
            if tx.get('status') == 'Cleared':
                amt = float(tx.get('amount', 0.0))
                ttype = tx.get('transaction_type')
                if ttype == 'Capital Influx':
                    total_inflow += amt
                elif ttype in ('Capital Withdrawal', 'Interest Payout', 'Dividend Payout'):
                    total_outflow += amt

        loan_principal = sum(
            float(l.get('principal_amount', 0.0)) for l in loans
        )
        total_outstanding = sum(
            float(l.get('outstanding_balance', 0.0)) for l in loans if l.get('status') == 'Active'
        )
        total_outbound_alloc = sum(
            float(o.get('allocated_capital', 0.0)) for o in outbound if o.get('status') == 'Active'
        )
        total_capital_managed = total_inflow - total_outflow + total_outstanding

        interest_due = sum(
            float(s.get('scheduled_interest', 0.0))
            for s in schedules if s.get('payment_status') == 'Unpaid'
        )

        monthly_trend = ReportService._monthly_capital_trend(transactions, loans)
        source_breakdown = {
            'Investor Capital Inflow': round(total_inflow, 2),
            'Active Loan Principal': round(loan_principal, 2),
            'Outbound Allocations': round(total_outbound_alloc, 2),
        }

        return {
            'total_capital_managed': round(total_capital_managed, 2),
            'total_inflow': round(total_inflow, 2),
            'total_outflow': round(total_outflow, 2),
            'total_outstanding': round(total_outstanding, 2),
            'total_outbound_allocated': round(total_outbound_alloc, 2),
            'interest_due': round(interest_due, 2),
            'investors_count': len(investors),
            'loan_principal_total': round(loan_principal, 2),
            'source_breakdown': source_breakdown,
            'monthly_trend': monthly_trend,
        }

    @staticmethod
    def _monthly_capital_trend(transactions, loans):
        trend = defaultdict(lambda: {'inflow': 0.0, 'outflow': 0.0})
        for tx in transactions:
            if tx.get('status') == 'Cleared' and tx.get('value_date'):
                try:
                    d = datetime.strptime(tx['value_date'], '%Y-%m-%d')
                    key = d.strftime('%Y-%m')
                    amt = float(tx.get('amount', 0.0))
                    ttype = tx.get('transaction_type')
                    if ttype == 'Capital Influx':
                        trend[key]['inflow'] += amt
                    elif ttype in ('Capital Withdrawal', 'Interest Payout', 'Dividend Payout'):
                        trend[key]['outflow'] += amt
                except (ValueError, TypeError):
                    continue
        labels = sorted(trend.keys())
        return {
            'labels': labels,
            'inflow': [round(trend[m]['inflow'], 2) for m in labels],
            'outflow': [round(trend[m]['outflow'], 2) for m in labels],
        }

    # ── Loan Portfolio ───────────────────────────────────────────

    @staticmethod
    def loan_portfolio():
        loans = fs.get_collection(COLL_LOANS)
        investors = {i['id']: i for i in fs.get_collection(COLL_INVESTORS)}

        by_status = defaultdict(lambda: {'count': 0, 'principal': 0.0, 'outstanding': 0.0})
        by_category = defaultdict(lambda: {'count': 0, 'principal': 0.0})

        total_principal = 0.0
        total_outstanding = 0.0

        for loan in loans:
            status = loan.get('status', 'Active')
            principal = float(loan.get('principal_amount', 0.0))
            outstanding = float(loan.get('outstanding_balance', 0.0))
            total_principal += principal
            total_outstanding += outstanding

            by_status[status]['count'] += 1
            by_status[status]['principal'] += principal
            by_status[status]['outstanding'] += outstanding

            inv = investors.get(loan.get('investor_id', ''))
            cat = inv.get('category', 'Unknown') if inv else 'Unknown'
            by_category[cat]['count'] += 1
            by_category[cat]['principal'] += principal

        active_count = by_status.get('Active', {}).get('count', 0)
        paid_count = by_status.get('Fully Paid', {}).get('count', 0)
        defaulted_count = by_status.get('Defaulted', {}).get('count', 0)

        return {
            'total_loans': len(loans),
            'total_principal': round(total_principal, 2),
            'total_outstanding': round(total_outstanding, 2),
            'active_count': active_count,
            'paid_count': paid_count,
            'defaulted_count': defaulted_count,
            'by_status': dict(by_status),
            'by_category': dict(by_category),
        }

    # ── P&L Statement ────────────────────────────────────────────

    @staticmethod
    def pl_summary():
        pl_entries = fs.get_collection(COLL_PL_LEDGER)
        schedules = fs.get_collection(COLL_LOAN_SCHEDULES)

        sorted_entries = sorted(pl_entries, key=lambda x: x.get('month', ''))
        total_revenue = 0.0
        total_opex = 0.0
        total_interest = 0.0
        total_net = 0.0

        monthly_data = []
        for entry in sorted_entries:
            rev = float(entry.get('revenue', 0.0))
            opex = float(entry.get('opex', 0.0))
            interest = float(entry.get('interest_expense', 0.0))
            net = float(entry.get('net_profit', 0.0))
            total_revenue += rev
            total_opex += opex
            total_interest += interest
            total_net += net
            monthly_data.append({
                'month': entry.get('month', ''),
                'revenue': rev,
                'opex': opex,
                'interest_expense': interest,
                'net_profit': net,
            })

        # Compute interest from schedules for months not yet in P&L
        computed_interest = {}
        for s in schedules:
            due = s.get('due_date', '')
            if due:
                month_key = due[:7]
                computed_interest[month_key] = computed_interest.get(month_key, 0.0) + float(
                    s.get('scheduled_interest', 0.0)
                )

        return {
            'total_revenue': round(total_revenue, 2),
            'total_opex': round(total_opex, 2),
            'total_interest_expense': round(total_interest, 2),
            'total_net_profit': round(total_net, 2),
            'monthly_data': monthly_data,
            'computed_interest': computed_interest,
            'months_covered': len(monthly_data),
        }

    # ── Investor Activity ────────────────────────────────────────

    @staticmethod
    def investor_activity():
        investors = fs.get_collection(COLL_INVESTORS)
        transactions = fs.get_collection(COLL_TRANSACTIONS)

        top_investors = defaultdict(lambda: {'inflow': 0.0, 'outflow': 0.0, 'count': 0})
        investor_map = {i['id']: i.get('name', 'Unknown') for i in investors}

        for tx in transactions:
            inv_id = tx.get('investor_id', '')
            if not inv_id:
                continue
            amt = float(tx.get('amount', 0.0))
            ttype = tx.get('transaction_type')
            top_investors[inv_id]['count'] += 1
            if ttype == 'Capital Influx':
                top_investors[inv_id]['inflow'] += amt
            else:
                top_investors[inv_id]['outflow'] += amt

        ranked = sorted(
            [
                {
                    'investor_id': k,
                    'investor_name': investor_map.get(k, 'Unknown'),
                    'inflow': round(v['inflow'], 2),
                    'outflow': round(v['outflow'], 2),
                    'net': round(v['inflow'] - v['outflow'], 2),
                    'transaction_count': v['count'],
                }
                for k, v in top_investors.items()
            ],
            key=lambda x: x['inflow'] + x['outflow'],
            reverse=True,
        )

        total_inflow = sum(r['inflow'] for r in ranked)
        total_outflow = sum(r['outflow'] for r in ranked)

        return {
            'total_investors': len(investors),
            'total_inflow': round(total_inflow, 2),
            'total_outflow': round(total_outflow, 2),
            'net_flow': round(total_inflow - total_outflow, 2),
            'top_investors': ranked[:10],
            'active_investor_count': len([i for i in investors if i.get('is_active')]),
        }

    # ── Instrument Performance ────────────────────────────────────

    @staticmethod
    def instrument_performance():
        instruments = fs.get_collection(COLL_INSTRUMENTS)

        by_type = defaultdict(lambda: {'count': 0, 'face_value_total': 0.0, 'units_total': 0})
        total_face_value = 0.0
        total_units = 0

        for inst in instruments:
            itype = inst.get('type', inst.get('instrument_type', 'Other'))
            fv = float(inst.get('face_value', 0.0))
            units = int(inst.get('total_units_issued', 0))
            total_face_value += fv
            total_units += units
            by_type[itype]['count'] += 1
            by_type[itype]['face_value_total'] += fv
            by_type[itype]['units_total'] += units

        return {
            'total_instruments': len(instruments),
            'total_face_value': round(total_face_value, 2),
            'total_units_issued': total_units,
            'by_type': dict(by_type),
            'instruments': [
                {
                    'code': inst.get('instrument_code', ''),
                    'type': inst.get('type', inst.get('instrument_type', 'Other')),
                    'face_value': float(inst.get('face_value', 0.0)),
                    'units_issued': int(inst.get('total_units_issued', 0)),
                    'units_outstanding': int(inst.get('units_outstanding', 0)),
                    'issue_date': inst.get('issue_date', ''),
                    'maturity_date': inst.get('maturity_date', ''),
                    'sector': inst.get('sector', ''),
                    'isin': inst.get('isin', ''),
                }
                for inst in instruments
            ],
        }


# ── View Helpers ──────────────────────────────────────────────

def reports_dashboard(request):
    """Render the analytics & reports dashboard."""
    import json
    from django.shortcuts import render

    class DecimalEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, Decimal):
                return float(obj)
            if isinstance(obj, datetime):
                return obj.isoformat()
            if isinstance(obj, date):
                return obj.isoformat()
            return super().default(obj)

    overview = ReportService.capital_overview()
    loan = ReportService.loan_portfolio()
    pl = ReportService.pl_summary()
    activity = ReportService.investor_activity()
    instruments = ReportService.instrument_performance()

    context = {
        'overview': overview,
        'loan_portfolio': loan,
        'pl_summary': pl,
        'investor_activity': activity,
        'instrument_performance': instruments,
        'overview_json': json.dumps(overview, cls=DecimalEncoder),
        'loan_portfolio_json': json.dumps(loan, cls=DecimalEncoder),
        'pl_summary_json': json.dumps(pl, cls=DecimalEncoder),
        'investor_activity_json': json.dumps(activity, cls=DecimalEncoder),
        'instrument_performance_json': json.dumps(instruments, cls=DecimalEncoder),
    }
    return render(request, 'investment/reports.html', context)


def report_data_json(request, report_name):
    """Return JSON data for a specific report (Chart.js consumption)."""
    from django.http import JsonResponse

    services = {
        'capital_overview': ReportService.capital_overview,
        'loan_portfolio': ReportService.loan_portfolio,
        'pl_summary': ReportService.pl_summary,
        'investor_activity': ReportService.investor_activity,
        'instrument_performance': ReportService.instrument_performance,
    }

    service = services.get(report_name)
    if not service:
        return JsonResponse({'error': f'Unknown report: {report_name}'}, status=404)

    try:
        data = service()
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def export_csv(request, report_name):
    """Export a report as a CSV file download."""
    services = {
        'capital_overview': _export_capital_overview_csv,
        'loan_portfolio': _export_loan_portfolio_csv,
        'pl_summary': _export_pl_csv,
        'investor_activity': _export_investor_activity_csv,
        'instrument_performance': _export_instruments_csv,
    }

    exporter = services.get(report_name)
    if not exporter:
        from django.http import JsonResponse
        return JsonResponse({'error': f'Unknown report: {report_name}'}, status=404)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{report_name}_{date.today().isoformat()}.csv"'
    exporter(response)
    return response


def _export_capital_overview_csv(response):
    data = ReportService.capital_overview()
    writer = csv.writer(response)
    writer.writerow(['Metric', 'Value (BDT)'])
    writer.writerow(['Total Capital Managed', data['total_capital_managed']])
    writer.writerow(['Total Inflow', data['total_inflow']])
    writer.writerow(['Total Outflow', data['total_outflow']])
    writer.writerow(['Total Outstanding', data['total_outstanding']])
    writer.writerow(['Outbound Allocated', data['total_outbound_allocated']])
    writer.writerow(['Interest Due', data['interest_due']])
    writer.writerow(['Investors', data['investors_count']])
    writer.writerow([])
    writer.writerow(['Month', 'Inflow', 'Outflow'])
    trend = data.get('monthly_trend', {})
    for i, label in enumerate(trend.get('labels', [])):
        inflow = trend['inflow'][i] if i < len(trend['inflow']) else 0
        outflow = trend['outflow'][i] if i < len(trend['outflow']) else 0
        writer.writerow([label, inflow, outflow])


def _export_loan_portfolio_csv(response):
    data = ReportService.loan_portfolio()
    writer = csv.writer(response)
    writer.writerow(['Loan Portfolio Summary'])
    writer.writerow(['Total Loans', data['total_loans']])
    writer.writerow(['Total Principal', data['total_principal']])
    writer.writerow(['Total Outstanding', data['total_outstanding']])
    writer.writerow(['Active', data['active_count']])
    writer.writerow(['Fully Paid', data['paid_count']])
    writer.writerow(['Defaulted', data['defaulted_count']])
    writer.writerow([])
    writer.writerow(['Status', 'Count', 'Principal', 'Outstanding'])
    for status, vals in data.get('by_status', {}).items():
        writer.writerow([status, vals['count'], vals['principal'], vals['outstanding']])


def _export_pl_csv(response):
    data = ReportService.pl_summary()
    writer = csv.writer(response)
    writer.writerow(['P&L Statement Summary'])
    writer.writerow(['Total Revenue', data['total_revenue']])
    writer.writerow(['Total OPEX', data['total_opex']])
    writer.writerow(['Interest Expense', data['total_interest_expense']])
    writer.writerow(['Net Profit', data['total_net_profit']])
    writer.writerow([])
    writer.writerow(['Month', 'Revenue', 'OPEX', 'Interest', 'Net Profit'])
    for m in data.get('monthly_data', []):
        writer.writerow([m['month'], m['revenue'], m['opex'], m['interest_expense'], m['net_profit']])


def _export_investor_activity_csv(response):
    data = ReportService.investor_activity()
    writer = csv.writer(response)
    writer.writerow(['Investor Activity Summary'])
    writer.writerow(['Total Investors', data['total_investors']])
    writer.writerow(['Active Investors', data['active_investor_count']])
    writer.writerow(['Total Inflow', data['total_inflow']])
    writer.writerow(['Total Outflow', data['total_outflow']])
    writer.writerow(['Net Flow', data['net_flow']])
    writer.writerow([])
    writer.writerow(['Investor', 'Inflow', 'Outflow', 'Net', 'Transactions'])
    for inv in data.get('top_investors', []):
        writer.writerow([inv['investor_name'], inv['inflow'], inv['outflow'], inv['net'], inv['transaction_count']])


def _export_instruments_csv(response):
    data = ReportService.instrument_performance()
    writer = csv.writer(response)
    writer.writerow(['Instrument Performance Summary'])
    writer.writerow(['Total Instruments', data['total_instruments']])
    writer.writerow(['Total Face Value', data['total_face_value']])
    writer.writerow(['Total Units Issued', data['total_units_issued']])
    writer.writerow([])
    writer.writerow(['Code', 'Type', 'Face Value', 'Units Issued', 'Units Outstanding', 'Issue Date', 'Maturity', 'Sector', 'ISIN'])
    for inst in data.get('instruments', []):
        writer.writerow([
            inst['code'], inst['type'], inst['face_value'],
            inst['units_issued'], inst['units_outstanding'],
            inst['issue_date'], inst['maturity_date'],
            inst['sector'], inst['isin'],
        ])
