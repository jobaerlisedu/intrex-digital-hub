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
    money_to_float,
    money_to_str,
    COLL_INVESTORS,
    COLL_TRANSACTIONS,
    COLL_LOANS,
    COLL_LOAN_SCHEDULES,
    COLL_OUTBOUND,
    COLL_INSTRUMENTS,
    COLL_INSTRUMENT_PRICES,
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
                amt = money_to_float(tx.get('amount', 0.0))
                ttype = tx.get('transaction_type')
                if ttype == 'Capital Influx':
                    total_inflow += amt
                elif ttype in ('Capital Withdrawal', 'Interest Payout', 'Dividend Payout'):
                    total_outflow += amt

        loan_principal = sum(
            money_to_float(l.get('principal_amount', 0.0)) for l in loans
        )
        total_outstanding = sum(
            money_to_float(l.get('outstanding_balance', 0.0)) for l in loans if l.get('status') == 'Active'
        )
        total_outbound_alloc = sum(
            money_to_float(o.get('allocated_capital', 0.0)) for o in outbound if o.get('status') == 'Active'
        )
        total_capital_managed = total_inflow - total_outflow + total_outstanding

        interest_due = sum(
            money_to_float(s.get('scheduled_interest', 0.0))
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
                    amt = money_to_float(tx.get('amount', 0.0))
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
            principal = money_to_float(loan.get('principal_amount', 0.0))
            outstanding = money_to_float(loan.get('outstanding_balance', 0.0))
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
            rev = money_to_float(entry.get('revenue', 0.0))
            opex = money_to_float(entry.get('opex', 0.0))
            interest = money_to_float(entry.get('interest_expense', 0.0))
            net = money_to_float(entry.get('net_profit', 0.0))
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
                computed_interest[month_key] = computed_interest.get(month_key, 0.0) + money_to_float(
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
            amt = money_to_float(tx.get('amount', 0.0))
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
        prices = fs.get_collection(COLL_INSTRUMENT_PRICES)

        latest_prices = {}
        for p in prices:
            inv_id = p.get('instrument_id')
            p_date = p.get('price_date', '')
            p_price = money_to_float(p.get('price', 0.0))
            if inv_id and (inv_id not in latest_prices or p_date > latest_prices[inv_id]['date']):
                latest_prices[inv_id] = {'date': p_date, 'price': p_price}

        by_type = defaultdict(lambda: {'count': 0, 'face_value_total': 0.0, 'units_total': 0, 'market_value_total': 0.0})
        total_face_value = 0.0
        total_units = 0
        total_market_value = 0.0

        for inst in instruments:
            itype = inst.get('type', inst.get('instrument_type', 'Other'))
            fv = money_to_float(inst.get('face_value', 0.0))
            units = int(inst.get('total_units_issued', 0))
            instr_id = inst.get('id', '')
            lp = latest_prices.get(instr_id, {})
            mv = lp.get('price', 0.0) * units if lp else 0.0
            total_face_value += fv
            total_units += units
            total_market_value += mv
            by_type[itype]['count'] += 1
            by_type[itype]['face_value_total'] += fv
            by_type[itype]['units_total'] += units
            by_type[itype]['market_value_total'] += mv

        instr_list = []
        for inst in instruments:
            lp = latest_prices.get(inst.get('id', ''), {})
            instr_list.append({
                'code': inst.get('instrument_code', ''),
                'type': inst.get('type', inst.get('instrument_type', 'Other')),
                'face_value': money_to_float(inst.get('face_value', 0.0)),
                'units_issued': int(inst.get('total_units_issued', 0)),
                'units_outstanding': int(inst.get('units_outstanding', 0)),
                'issue_date': inst.get('issue_date', ''),
                'maturity_date': inst.get('maturity_date', ''),
                'sector': inst.get('sector', ''),
                'isin': inst.get('isin', ''),
                'latest_price': lp.get('price', 0.0),
                'market_value': round(lp.get('price', 0.0) * int(inst.get('units_outstanding', 0)), 2),
            })

        return {
            'total_instruments': len(instruments),
            'total_face_value': round(total_face_value, 2),
            'total_units_issued': total_units,
            'total_market_value': round(total_market_value, 2),
            'by_type': dict(by_type),
            'instruments': instr_list,
        }

    @staticmethod
    def nav_summary() -> dict:
        """NAV trend, AUM history, unit issuance/redemption activity."""
        from investment.services import NavService, COLL_NAV_HISTORY, COLL_INVESTOR_HOLDINGS
        nav_history = fs.get_collection(COLL_NAV_HISTORY)
        nav_history.sort(key=lambda r: r.get('nav_date', ''))

        holdings = fs.get_collection(COLL_INVESTOR_HOLDINGS)
        total_units = sum(money_to_float(h.get('units_held', '0.0000')) for h in holdings)
        total_invested = sum(money_to_float(h.get('total_invested', '0.00')) for h in holdings)
        total_value = sum(money_to_float(h.get('current_value', '0.00')) for h in holdings)

        current_nav = NavService.get_current_nav()

        return {
            'current_nav_per_unit': current_nav['nav_per_unit'] if current_nav else '0.0000',
            'current_aum': current_nav['total_aum'] if current_nav else '0.00',
            'total_units': f'{total_units:.4f}',
            'total_invested': f'{total_invested:.2f}',
            'total_value': f'{total_value:.2f}',
            'total_pl': f'{round(total_value - total_invested, 2):.2f}',
            'nav_history': nav_history,
        }

    @staticmethod
    def fee_impact() -> dict:
        """Show cumulative fees deducted from returns."""
        from investment.services import COLL_FEE_ACCRUALS
        fee_accruals = fs.get_collection(COLL_FEE_ACCRUALS)
        total_mgmt = sum(
            money_to_float(f.get('amount', '0.00'))
            for f in fee_accruals if f.get('fee_type') == 'management'
        )
        total_perf = sum(
            money_to_float(f.get('amount', '0.00'))
            for f in fee_accruals if f.get('fee_type') == 'performance'
        )
        return {
            'total_management_fees': f'{total_mgmt:.2f}',
            'total_performance_fees': f'{total_perf:.2f}',
            'total_fees': f'{round(total_mgmt + total_perf, 2):.2f}',
            'unsettled_management': f'{sum(money_to_float(f.get("amount", "0.00")) for f in fee_accruals if f.get("fee_type") == "management" and not f.get("is_settled", False)):.2f}',
            'unsettled_performance': f'{sum(money_to_float(f.get("amount", "0.00")) for f in fee_accruals if f.get("fee_type") == "performance" and not f.get("is_settled", False)):.2f}',
            'fee_accruals': fee_accruals,
        }

    @staticmethod
    def performance_metrics(investor_id: str | None = None) -> dict:
        """Aggregate all performance metrics.

        Uses NAV history and holding data. If investor_id is provided,
        metrics are scoped to that investor's holdings.
        """
        from investment.services import (
            PerformanceService as perf,
            COLL_NAV_HISTORY, COLL_INVESTOR_HOLDINGS,
        )

        nav_history = fs.get_collection(COLL_NAV_HISTORY)
        nav_history.sort(key=lambda r: r.get('nav_date', ''))

        holdings = fs.get_collection(COLL_INVESTOR_HOLDINGS)
        if investor_id:
            holdings = [h for h in holdings if h.get('investor_id') == investor_id]

        nav_values = [money_to_float(n.get('nav_per_unit', 0)) for n in nav_history if money_to_float(n.get('nav_per_unit', 0)) > 0]
        if len(nav_values) < 2:
            return {'error': 'Insufficient NAV data for performance calculation'}

        # Periodic returns from NAV series
        returns = []
        for i in range(1, len(nav_values)):
            if nav_values[i - 1] > 0:
                returns.append((nav_values[i] - nav_values[i - 1]) / nav_values[i - 1])

        twrr = perf.time_weighted_return(nav_history)
        max_dd = perf.max_drawdown(nav_history)
        rolling_12m = perf.rolling_return(nav_history, 12)
        total_invested = sum(money_to_float(h.get('total_invested', '0.00')) for h in holdings)
        total_value = sum(money_to_float(h.get('current_value', '0.00')) for h in holdings)
        total_return = (total_value - total_invested) / total_invested if total_invested > 0 else 0.0

        years = 0.0
        if len(nav_history) >= 2:
            first_date = nav_history[0].get('nav_date', '')
            last_date = nav_history[-1].get('nav_date', '')
            if first_date and last_date:
                from datetime import date
                try:
                    d1 = date.fromisoformat(first_date)
                    d2 = date.fromisoformat(last_date)
                    years = (d2 - d1).days / 365.25
                except ValueError:
                    years = 0.0

        return {
            'twrr': round(twrr * 100, 4),
            'mwrr': round(perf.money_weighted_return(
                [{'amount': total_invested, 'days_from_start': 0}],
                total_value,
            ) * 100, 4),
            'sharpe_ratio': perf.sharpe_ratio(returns),
            'sortino_ratio': perf.sortino_ratio(returns),
            'max_drawdown_pct': max_dd['max_drawdown_pct'],
            'peak_date': max_dd['peak_date'],
            'trough_date': max_dd['trough_date'],
            'cagr_since_inception': round(perf.annualized_return(total_return, years) * 100, 4) if years > 0 else 0.0,
            'cagr_1yr': 0.0,
            'cagr_3yr': 0.0,
            'cagr_5yr': 0.0,
            'rolling_12m_returns': rolling_12m,
            'volatility': round(perf.volatility(returns) * 100, 4),
            'win_rate': round(sum(1 for r in returns if r > 0) / len(returns) * 100, 2) if returns else 0.0,
            'total_return_pct': round(total_return * 100, 4),
            'total_invested': f'{total_invested:.2f}',
            'total_value': f'{total_value:.2f}',
        }

    @staticmethod
    def compliance_overview() -> dict:
        """Compliance dashboard: KYC status, concentration, sector exposure, alerts."""
        from investment.services import ComplianceService

        kyc = ComplianceService.kyc_compliance_report()
        concentrations = ComplianceService.all_investor_concentrations()
        sector_conc = ComplianceService.sector_concentration()
        instrument_conc = ComplianceService.instrument_concentration()

        breached = [c for c in concentrations if c['breached']]
        expired_kyc = [k for k in kyc if k['is_expired']]
        attention_kyc = [k for k in kyc if k['needs_attention']]

        return {
            'kyc_report': kyc,
            'kyc_summary': {
                'total_investors': len(kyc),
                'expired': len(expired_kyc),
                'needs_attention': len(attention_kyc),
                'compliant': len(kyc) - len(attention_kyc),
            },
            'concentrations': concentrations,
            'breaches': breached,
            'breach_count': len(breached),
            'sector_concentration': sector_conc,
            'instrument_concentration': instrument_conc,
        }

    @staticmethod
    def cash_flow_forecast(months: int = 12) -> dict:
        """Combined view: projected inflows (repayments) vs outflows (calls, expenses)."""
        from investment.services import CashFlowForecastService

        payables = CashFlowForecastService.forecast_payables(months)
        outbound = CashFlowForecastService.forecast_outbound_calls(months)
        nav_growth = CashFlowForecastService.forecast_nav_growth(months)
        scenario = CashFlowForecastService.what_if_default_rate()

        # Merge payables and outbound by month
        inflow_map = {p['month']: p['projected_inflow'] for p in payables}
        outflow_map = {o['month']: o['projected_outflow'] for o in outbound}
        aum_map = {n['month']: n['projected_aum'] for n in nav_growth}

        all_months = sorted(set(list(inflow_map.keys()) + list(outflow_map.keys()) + list(aum_map.keys())))

        monthly = []
        for m in all_months:
            monthly.append({
                'month': m,
                'projected_inflow': inflow_map.get(m, 0.0),
                'projected_outflow': outflow_map.get(m, 0.0),
                'net_flow': round(inflow_map.get(m, 0.0) - outflow_map.get(m, 0.0), 2),
                'projected_aum': aum_map.get(m, 0.0),
            })

        total_inflow = sum(r['projected_inflow'] for r in monthly)
        total_outflow = sum(r['projected_outflow'] for r in monthly)
        min_balance = min((r['projected_aum'] for r in monthly), default=0.0)
        liquidity_ratio = round(total_inflow / total_outflow, 4) if total_outflow > 0 else 0.0

        return {
            'monthly': monthly,
            'nav_growth': nav_growth,
            'scenario': scenario,
            'summary': {
                'total_projected_inflow': round(total_inflow, 2),
                'total_projected_outflow': round(total_outflow, 2),
                'net_projected': round(total_inflow - total_outflow, 2),
                'min_projected_aum': round(min_balance, 2),
                'liquidity_ratio': liquidity_ratio,
                'months_forecast': months,
            },
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
    performance = ReportService.performance_metrics()
    compliance = ReportService.compliance_overview()
    cashflow = ReportService.cash_flow_forecast()

    context = {
        'overview': overview,
        'loan_portfolio': loan,
        'pl_summary': pl,
        'investor_activity': activity,
        'instrument_performance': instruments,
        'performance_metrics': performance,
        'compliance': compliance,
        'cash_flow_forecast': cashflow,
        'overview_json': json.dumps(overview, cls=DecimalEncoder),
        'loan_portfolio_json': json.dumps(loan, cls=DecimalEncoder),
        'pl_summary_json': json.dumps(pl, cls=DecimalEncoder),
        'investor_activity_json': json.dumps(activity, cls=DecimalEncoder),
        'instrument_performance_json': json.dumps(instruments, cls=DecimalEncoder),
        'performance_metrics_json': json.dumps(performance, cls=DecimalEncoder),
        'compliance_json': json.dumps(compliance, cls=DecimalEncoder),
        'cash_flow_forecast_json': json.dumps(cashflow, cls=DecimalEncoder),
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
        'performance_metrics': ReportService.performance_metrics,
        'compliance': ReportService.compliance_overview,
        'cash_flow_forecast': ReportService.cash_flow_forecast,
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
        'performance_metrics': _export_performance_csv,
        'compliance': _export_compliance_csv,
        'cash_flow_forecast': _export_cashflow_csv,
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
    writer.writerow(['Total Capital Managed', money_to_str(data['total_capital_managed'])])
    writer.writerow(['Total Inflow', money_to_str(data['total_inflow'])])
    writer.writerow(['Total Outflow', money_to_str(data['total_outflow'])])
    writer.writerow(['Total Outstanding', money_to_str(data['total_outstanding'])])
    writer.writerow(['Outbound Allocated', money_to_str(data['total_outbound_allocated'])])
    writer.writerow(['Interest Due', money_to_str(data['interest_due'])])
    writer.writerow(['Investors', data['investors_count']])
    writer.writerow([])
    writer.writerow(['Month', 'Inflow', 'Outflow'])
    trend = data.get('monthly_trend', {})
    for i, label in enumerate(trend.get('labels', [])):
        inflow = trend['inflow'][i] if i < len(trend['inflow']) else 0
        outflow = trend['outflow'][i] if i < len(trend['outflow']) else 0
        writer.writerow([label, money_to_str(inflow), money_to_str(outflow)])


def _export_loan_portfolio_csv(response):
    data = ReportService.loan_portfolio()
    writer = csv.writer(response)
    writer.writerow(['Loan Portfolio Summary'])
    writer.writerow(['Total Loans', data['total_loans']])
    writer.writerow(['Total Principal', money_to_str(data['total_principal'])])
    writer.writerow(['Total Outstanding', money_to_str(data['total_outstanding'])])
    writer.writerow(['Active', data['active_count']])
    writer.writerow(['Fully Paid', data['paid_count']])
    writer.writerow(['Defaulted', data['defaulted_count']])
    writer.writerow([])
    writer.writerow(['Status', 'Count', 'Principal', 'Outstanding'])
    for status, vals in data.get('by_status', {}).items():
        writer.writerow([status, vals['count'], money_to_str(vals['principal']), money_to_str(vals['outstanding'])])


def _export_pl_csv(response):
    data = ReportService.pl_summary()
    writer = csv.writer(response)
    writer.writerow(['P&L Statement Summary'])
    writer.writerow(['Total Revenue', money_to_str(data['total_revenue'])])
    writer.writerow(['Total OPEX', money_to_str(data['total_opex'])])
    writer.writerow(['Interest Expense', money_to_str(data['total_interest_expense'])])
    writer.writerow(['Net Profit', money_to_str(data['total_net_profit'])])
    writer.writerow([])
    writer.writerow(['Month', 'Revenue', 'OPEX', 'Interest', 'Net Profit'])
    for m in data.get('monthly_data', []):
        writer.writerow([m['month'], money_to_str(m['revenue']), money_to_str(m['opex']), money_to_str(m['interest_expense']), money_to_str(m['net_profit'])])


def _export_investor_activity_csv(response):
    data = ReportService.investor_activity()
    writer = csv.writer(response)
    writer.writerow(['Investor Activity Summary'])
    writer.writerow(['Total Investors', data['total_investors']])
    writer.writerow(['Active Investors', data['active_investor_count']])
    writer.writerow(['Total Inflow', money_to_str(data['total_inflow'])])
    writer.writerow(['Total Outflow', money_to_str(data['total_outflow'])])
    writer.writerow(['Net Flow', money_to_str(data['net_flow'])])
    writer.writerow([])
    writer.writerow(['Investor', 'Inflow', 'Outflow', 'Net', 'Transactions'])
    for inv in data.get('top_investors', []):
        writer.writerow([inv['investor_name'], money_to_str(inv['inflow']), money_to_str(inv['outflow']), money_to_str(inv['net']), inv['transaction_count']])


def _export_instruments_csv(response):
    data = ReportService.instrument_performance()
    writer = csv.writer(response)
    writer.writerow(['Instrument Performance Summary'])
    writer.writerow(['Total Instruments', data['total_instruments']])
    writer.writerow(['Total Face Value', money_to_str(data['total_face_value'])])
    writer.writerow(['Total Units Issued', data['total_units_issued']])
    writer.writerow(['Total Market Value', money_to_str(data.get('total_market_value', 0.0))])
    writer.writerow([])
    writer.writerow(['Code', 'Type', 'Face Value', 'Units Issued', 'Units Outstanding', 'Issue Date', 'Maturity', 'Sector', 'ISIN', 'Latest Price', 'Market Value'])
    for inst in data.get('instruments', []):
        writer.writerow([
            inst['code'], inst['type'], money_to_str(inst['face_value']),
            inst['units_issued'], inst['units_outstanding'],
            inst['issue_date'], inst['maturity_date'],
            inst['sector'], inst['isin'],
            money_to_str(inst.get('latest_price', 0.0)), money_to_str(inst.get('market_value', 0.0)),
        ])


def _export_performance_csv(response):
    """Per-investor or aggregate performance data."""
    data = ReportService.performance_metrics()
    writer = csv.writer(response)
    writer.writerow(['Performance Metrics Summary'])
    writer.writerow(['Metric', 'Value'])
    writer.writerow(['TWRR (%)', data.get('twrr', 'N/A')])
    writer.writerow(['MWRR/IRR (%)', data.get('mwrr', 'N/A')])
    writer.writerow(['Sharpe Ratio', data.get('sharpe_ratio', 'N/A')])
    writer.writerow(['Sortino Ratio', data.get('sortino_ratio', 'N/A')])
    writer.writerow(['Max Drawdown (%)', data.get('max_drawdown_pct', 'N/A')])
    writer.writerow(['Peak Date', data.get('peak_date', 'N/A')])
    writer.writerow(['Trough Date', data.get('trough_date', 'N/A')])
    writer.writerow(['CAGR Since Inception (%)', data.get('cagr_since_inception', 'N/A')])
    writer.writerow(['Volatility (%)', data.get('volatility', 'N/A')])
    writer.writerow(['Win Rate (%)', data.get('win_rate', 'N/A')])
    writer.writerow(['Total Return (%)', data.get('total_return_pct', 'N/A')])
    writer.writerow(['Total Invested', data.get('total_invested', 'N/A')])
    writer.writerow(['Total Value', data.get('total_value', 'N/A')])
    rolling = data.get('rolling_12m_returns', [])
    if rolling:
        writer.writerow([])
        writer.writerow(['Date', 'Rolling 12m Return (%)'])
        for r in rolling:
            writer.writerow([r['date'], round(r['return'] * 100, 4)])


def _export_compliance_csv(response):
    """Export compliance overview: KYC status, concentration, breaches."""
    data = ReportService.compliance_overview()
    writer = csv.writer(response)

    writer.writerow(['Compliance Overview'])
    kyc = data.get('kyc_summary', {})
    writer.writerow(['KYC Summary'])
    writer.writerow(['Total Investors', kyc.get('total_investors', 0)])
    writer.writerow(['Expired KYC', kyc.get('expired', 0)])
    writer.writerow(['Needs Attention', kyc.get('needs_attention', 0)])
    writer.writerow(['Compliant', kyc.get('compliant', 0)])

    kyc_report = data.get('kyc_report', [])
    if kyc_report:
        writer.writerow([])
        writer.writerow(['Investor', 'KYC Status', 'Expiry Date', 'Has Document', 'Expired', 'Expires Soon'])
        for r in kyc_report:
            writer.writerow([
                r['investor_name'], r['kyc_status'], r.get('kyc_expiry_date', ''),
                'Yes' if r['has_document'] else 'No', 'Yes' if r['is_expired'] else 'No',
                'Yes' if r['expires_soon'] else 'No',
            ])

    breaches = data.get('breaches', [])
    if breaches:
        writer.writerow([])
        writer.writerow(['Concentration Breaches'])
        writer.writerow(['Investor', 'Concentration %', 'Threshold %'])
        for b in breaches:
            writer.writerow([b['investor_name'], b['concentration_pct'], b['threshold_pct']])

    sector = data.get('sector_concentration', {})
    sectors = sector.get('sectors', [])
    if sectors:
        writer.writerow([])
        writer.writerow(['Sector Concentration'])
        writer.writerow(['Sector', 'Outstanding (BDT)', 'Concentration %'])
        for s in sectors:
            writer.writerow([s['sector'], s['outstanding'], s['concentration_pct']])


def _export_cashflow_csv(response):
    """Export cash flow forecast data."""
    data = ReportService.cash_flow_forecast(12)
    writer = csv.writer(response)
    writer.writerow(['Cash Flow Forecast'])
    summary = data.get('summary', {})
    writer.writerow(['Total Projected Inflow', summary.get('total_projected_inflow', 0)])
    writer.writerow(['Total Projected Outflow', summary.get('total_projected_outflow', 0)])
    writer.writerow(['Net Projected', summary.get('net_projected', 0)])
    writer.writerow(['Min Projected AUM', summary.get('min_projected_aum', 0)])
    writer.writerow(['Liquidity Ratio', summary.get('liquidity_ratio', 0)])
    writer.writerow(['Months Forecast', summary.get('months_forecast', 12)])

    monthly = data.get('monthly', [])
    if monthly:
        writer.writerow([])
        writer.writerow(['Month', 'Projected Inflow', 'Projected Outflow', 'Net Flow', 'Projected AUM'])
        for m in monthly:
            writer.writerow([m['month'], m['projected_inflow'], m['projected_outflow'], m['net_flow'], m.get('projected_aum', 0)])

    nav = data.get('nav_growth', [])
    if nav:
        writer.writerow([])
        writer.writerow(['Month', 'Projected AUM', 'NAV per Unit', 'Investment Return', 'Fee Deduction'])
        for n in nav:
            writer.writerow([n['month'], n['projected_aum'], n['nav_per_unit'], n['investment_return'], n['fee_deduction']])

    scenario = data.get('scenario', {})
    if scenario:
        writer.writerow([])
        writer.writerow(['Scenario Analysis'])
        writer.writerow(['Current AUM', scenario.get('current_aum', 'N/A')])
        writer.writerow(['Base Default Rate', scenario.get('base_default_rate', 0)])
        writer.writerow(['Stress Default Rate', scenario.get('stress_default_rate', 0)])
        writer.writerow(['Base Loss', scenario.get('base_loss', 'N/A')])
        writer.writerow(['Stress Loss', scenario.get('stress_loss', 'N/A')])
        writer.writerow(['Base AUM After', scenario.get('base_aum_after', 'N/A')])
        writer.writerow(['Stress AUM After', scenario.get('stress_aum_after', 'N/A')])
