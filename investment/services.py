"""
Investment Service Layer

Django ORM-based data access and business logic.
"""

from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from dateutil.relativedelta import relativedelta
from typing import Optional
from math import isnan, isinf
from statistics import stdev, mean
from django.db import models as db_models, transaction
from django.db.models import Sum, Q
from django.utils import timezone
from config.logger import investment_logger

from investment.models import (
    Investor, Transaction, Loan, LoanSchedule,
    OutboundPlacement, FinancialInstrument, InstrumentPrice,
    PLLedger, NavHistory, InvestorHolding,
    FeeStructure, FeeAccrual, Counter,
)


# ──────────────────────────────────────────────
# Collection name constants (backward compat)
# ──────────────────────────────────────────────

COLL_INVESTORS = 'invst_investors'
COLL_TRANSACTIONS = 'invst_transactions'
COLL_LOANS = 'invst_loans'
COLL_LOAN_SCHEDULES = 'invst_loan_schedules'
COLL_OUTBOUND = 'invst_outbound_placements'
COLL_INSTRUMENTS = 'invst_financial_instruments'
COLL_INSTRUMENT_PRICES = 'invst_instrument_prices'
COLL_PL_LEDGER = 'invst_pl_ledger'
COLL_NAV_HISTORY = 'invst_nav_history'
COLL_INVESTOR_HOLDINGS = 'invst_investor_holdings'
COLL_FEE_STRUCTURES = 'invst_fee_structures'
COLL_FEE_ACCRUALS = 'invst_fee_accruals'
COLL_CURRENCY_CONFIG = 'invst_currency_config'
COLL_FX_RATES = 'invst_fx_rates'
COLL_COUNTERS = 'system_counters'


# ──────────────────────────────────────────────
# Monetary helpers — BDT string ↔ float conversion
# ──────────────────────────────────────────────

_BDT_PREFIX = 'BDT '


def money_to_str(value: float | int | str | None) -> str:
    if value is None:
        return f'{_BDT_PREFIX}0.00'
    if isinstance(value, str):
        value = money_to_float(value)
    formatted = f'{value:,.2f}'
    parts = formatted.split('.')
    integer_part = parts[0]
    if ',' in integer_part:
        groups = integer_part.split(',')
        last = groups[-1]
        rest = groups[:-1]
        combined = ''.join(rest)
        if len(combined) <= 2:
            indian_groups = [combined, last]
        else:
            rev = combined[::-1]
            pairs = [rev[i:i+2] for i in range(0, len(rev), 2)]
            indian_groups = [p[::-1] for p in reversed(pairs)] + [last]
        integer_part = ','.join(indian_groups)
    return f'{_BDT_PREFIX}{integer_part}.{parts[1]}'


def money_to_float(value: str | float | int | None) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = value.strip()
    if cleaned.startswith(_BDT_PREFIX):
        cleaned = cleaned[len(_BDT_PREFIX):]
    cleaned = cleaned.replace(',', '')
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return 0.0


def money_add(*values: str | float | int | None) -> float:
    total = 0.0
    for v in values:
        total += money_to_float(v)
    return total


def money_to_storage(value: str | float | int | None) -> str:
    return f'{money_to_float(value):.2f}'


# ══════════════════════════════════════════════
# MODEL REPOSITORY — Django ORM document CRUD
# ══════════════════════════════════════════════

_MODEL_MAP = {
    COLL_INVESTORS: Investor,
    COLL_TRANSACTIONS: Transaction,
    COLL_LOANS: Loan,
    COLL_LOAN_SCHEDULES: LoanSchedule,
    COLL_OUTBOUND: OutboundPlacement,
    COLL_INSTRUMENTS: FinancialInstrument,
    COLL_INSTRUMENT_PRICES: InstrumentPrice,
    COLL_PL_LEDGER: PLLedger,
    COLL_NAV_HISTORY: NavHistory,
    COLL_INVESTOR_HOLDINGS: InvestorHolding,
    COLL_FEE_STRUCTURES: FeeStructure,
    COLL_FEE_ACCRUALS: FeeAccrual,
}


def _model_for(collection_name: str):
    model = _MODEL_MAP.get(collection_name)
    if not model:
        raise ValueError(f"Unknown collection: {collection_name}")
    return model


def _model_to_dict(instance) -> dict:
    """Convert a model instance to a dict."""
    d = {}
    for field in instance._meta.fields:
        name = field.attname
        value = getattr(instance, name)
        if isinstance(value, (date, datetime)):
            value = value.isoformat()
        elif isinstance(value, Decimal):
            value = float(value)
        d[name if name != 'id' else 'id'] = value
    # Add related FK display fields
    if hasattr(instance, 'investor_id') and instance.investor_id:
        d['investor_id'] = str(instance.investor_id)
    if hasattr(instance, 'loan_id') and instance.loan_id:
        d['loan_id'] = str(instance.loan_id)
    if hasattr(instance, 'instrument_id') and instance.instrument_id:
        d['instrument_id'] = str(instance.instrument_id)
    if hasattr(instance, 'investor') and instance.investor:
        d['investor_name'] = instance.investor.name if hasattr(instance.investor, 'name') else ''
    return d


class ORMDocumentService:
    """Django ORM-backed document CRUD service."""

    @staticmethod
    def get_collection(collection_name: str,
                       where_filters: Optional[list[tuple[str, str, object]]] = None
                       ) -> list[dict]:
        model = _model_for(collection_name)
        qs = model.objects.filter(is_active=True)
        if where_filters:
            for field, op, value in where_filters:
                django_field = field.replace('investor_id', 'investor__id') if field == 'investor_id' else field
                django_field = django_field.replace('loan_id', 'loan__id') if field == 'loan_id' else field
                django_field = django_field.replace('instrument_id', 'instrument__id') if field == 'instrument_id' else field
                if op == '==':
                    qs = qs.filter(**{django_field: value})
                elif op == '<':
                    qs = qs.filter(**{f'{django_field}__lt': value})
                elif op == '<=':
                    qs = qs.filter(**{f'{django_field}__lte': value})
                elif op == '>':
                    qs = qs.filter(**{f'{django_field}__gt': value})
                elif op == '>=':
                    qs = qs.filter(**{f'{django_field}__gte': value})
                elif op == '!=':
                    qs = qs.exclude(**{django_field: value})
                elif op == 'in':
                    qs = qs.filter(**{f'{django_field}__in': value})
        return [_model_to_dict(obj) for obj in qs]

    @staticmethod
    def get_document(collection_name: str, doc_id: str) -> Optional[dict]:
        model = _model_for(collection_name)
        try:
            obj = model.objects.get(pk=doc_id)
            return _model_to_dict(obj)
        except model.DoesNotExist:
            return None
        except Exception as e:
            investment_logger.error(f"ORM get error [{collection_name}/{doc_id}]: {e}")
            return None

    @staticmethod
    def create_document(collection_name: str, data: dict) -> Optional[str]:
        model = _model_for(collection_name)
        try:
            cleaned = {}
            for field in model._meta.fields:
                if field.attname in data:
                    cleaned[field.attname] = data[field.attname]
            # Handle FK fields
            for fk_field in ('investor_id', 'loan_id', 'instrument_id'):
                fk_name = fk_field.replace('_id', '')
                if fk_field in data and hasattr(model, fk_name):
                    fk_model = model._meta.get_field(fk_name).related_model
                    try:
                        fk_obj = fk_model.objects.get(pk=data[fk_field])
                        cleaned[fk_name] = fk_obj
                    except fk_model.DoesNotExist:
                        pass
            obj = model.objects.create(**cleaned)
            return str(obj.pk)
        except Exception as e:
            investment_logger.error(f"ORM create error [{collection_name}]: {e}")
            return None

    @staticmethod
    def update_document(collection_name: str, doc_id: str, data: dict) -> bool:
        model = _model_for(collection_name)
        try:
            obj = model.objects.get(pk=doc_id)
            for key, value in data.items():
                if key in ('created_at', 'updated_at', 'id'):
                    continue
                if value is not None and key in [f.attname for f in model._meta.fields]:
                    setattr(obj, key, value)
            obj.save()
            return True
        except model.DoesNotExist:
            return False
        except Exception as e:
            investment_logger.error(f"ORM update error [{collection_name}/{doc_id}]: {e}")
            return False

    @staticmethod
    def delete_document(collection_name: str, doc_id: str) -> bool:
        model = _model_for(collection_name)
        try:
            model.objects.filter(pk=doc_id).delete()
            return True
        except Exception as e:
            investment_logger.error(f"ORM delete error [{collection_name}/{doc_id}]: {e}")
            return False

    @staticmethod
    def query_collection(collection_name: str, field: str, operator: str, value) -> list[dict]:
        return ORMDocumentService.get_collection(collection_name, [(field, operator, value)])

    @staticmethod
    def batch_write(operations: list[tuple]) -> bool:
        try:
            with transaction.atomic():
                for op in operations:
                    coll_name = op[1]
                    if op[0] == 'set':
                        ORMDocumentService.create_document(coll_name, op[3])
                    elif op[0] == 'update':
                        ORMDocumentService.update_document(coll_name, op[2], op[3])
                    elif op[0] == 'delete':
                        ORMDocumentService.delete_document(coll_name, op[2])
            return True
        except Exception as e:
            investment_logger.error(f"ORM batch error: {e}")
            return False


# ══════════════════════════════════════════════
# UNIQUE CODE GENERATION
# ══════════════════════════════════════════════

class CodeGenerator:
    """Generates unique sequential codes using a Django model counter."""

    @staticmethod
    def _next_sequence(counter_id: str, prefix: str, pad: int = 5) -> Optional[str]:
        try:
            with transaction.atomic():
                counter, created = Counter.objects.get_or_create(id=counter_id, defaults={'value': 1})
                if not created:
                    counter.value += 1
                    counter.save()
                seq = counter.value
            return f"{prefix}-{seq:0{pad}d}"
        except Exception as e:
            investment_logger.error(f"Code generation error [{counter_id}]: {e}")
            return None

    @staticmethod
    def investor_code() -> Optional[str]:
        return CodeGenerator._next_sequence('investor_code', 'INV', 5)

    @staticmethod
    def instrument_code() -> Optional[str]:
        return CodeGenerator._next_sequence('instrument_code', 'INST', 5)


def migrate_investor_codes():
    """One-time migration: seed the counter from existing max code."""
    max_seq = 0
    for inv in Investor.objects.iterator():
        code = getattr(inv, 'investor_code', '')
        if code.startswith('INV-'):
            try:
                seq = int(code.split('-')[1])
                max_seq = max(max_seq, seq)
            except (IndexError, ValueError):
                continue
    if max_seq > 0:
        Counter.objects.get_or_create(id='investor_code', defaults={'value': max_seq})


# ══════════════════════════════════════════════
# AMORTIZATION ENGINE (PMT Formula)
# ══════════════════════════════════════════════

class AmortizationService:
    """PMT-based equal-installment amortization schedule generator."""

    @staticmethod
    def compute_pmt(principal: float, annual_rate_pct: float, months: int) -> float:
        if months <= 0:
            return 0.0
        if annual_rate_pct == 0:
            return round(principal / months, 2)
        r = (annual_rate_pct / 100.0) / 12.0
        pmt = principal * (r * (1 + r) ** months) / ((1 + r) ** months - 1)
        return round(pmt, 2)

    @staticmethod
    def generate_schedule(
        principal: float,
        annual_rate_pct: float,
        months: int,
        disbursement_date: date,
        loan_id: str,
    ) -> list[dict]:
        r = (annual_rate_pct / 100.0) / 12.0
        pmt = AmortizationService.compute_pmt(principal, annual_rate_pct, months)
        balance = Decimal(str(principal))
        schedule = []

        for i in range(1, months + 1):
            interest = float((balance * Decimal(str(r))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
            principal_part = pmt - interest

            if i == months:
                principal_part = float(balance)
                pmt = round(principal_part + interest, 2)

            balance -= Decimal(str(principal_part))
            due_date = disbursement_date + relativedelta(months=i)

            schedule.append({
                'loan_id': loan_id,
                'installment_number': i,
                'due_date': due_date.isoformat(),
                'scheduled_principal': f'{round(principal_part, 2):.2f}',
                'scheduled_interest': f'{round(interest, 2):.2f}',
                'paid_amount': '0.00',
                'payment_status': 'Unpaid',
            })

        return schedule

    @staticmethod
    def compute_interest_expense(month_str: str, schedules: list[dict]) -> float:
        return sum(
            float(s.get('scheduled_interest', 0.0))
            for s in schedules
            if s.get('due_date', '').startswith(month_str)
        )


# ══════════════════════════════════════════════
# NAV ENGINE
# ══════════════════════════════════════════════

class NavService:
    """NAV calculation, unit issuance, and redemption."""

    @staticmethod
    def calculate_nav(nav_date: date) -> dict:
        transactions = Transaction.objects.filter(is_active=True)
        loans = Loan.objects.filter(is_active=True)
        outbound = OutboundPlacement.objects.filter(is_active=True)
        schedules = LoanSchedule.objects.filter(is_active=True)
        holdings = InvestorHolding.objects.filter(is_active=True)
        fee_accruals = FeeAccrual.objects.filter(is_active=True)

        cash = 0.0
        for tx in transactions:
            if tx.status == 'Cleared':
                amt = float(tx.amount)
                if tx.transaction_type == 'Capital Influx':
                    cash += amt
                elif tx.transaction_type in ('Capital Withdrawal', 'Interest Payout', 'Dividend Payout'):
                    cash -= amt

        loan_outstanding = sum(
            float(l.outstanding_balance) for l in loans if l.status == 'Active'
        )

        outbound_valuation = sum(
            float(o.current_valuation) for o in outbound if o.status == 'Active'
        )

        total_assets = cash + loan_outstanding + outbound_valuation

        unpaid_interest = sum(
            float(s.scheduled_interest)
            for s in schedules if s.payment_status in ('Unpaid', 'Overdue')
        )

        unpaid_fees = sum(
            float(f.amount) for f in fee_accruals if not f.is_settled
        )

        total_liabilities = unpaid_interest + unpaid_fees
        total_aum = round(max(total_assets - total_liabilities, 0.0), 2)
        total_units = sum(float(h.units_held) for h in holdings if h.is_active)

        nav_per_unit = round(total_aum / total_units, 4) if total_units > 0 else 0.0

        result = {
            'nav_date': nav_date.isoformat(),
            'nav_per_unit': f'{nav_per_unit:.4f}',
            'total_units': f'{total_units:.4f}',
            'total_aum': f'{total_aum:.2f}',
            'total_assets': f'{total_assets:.2f}',
            'total_liabilities': f'{total_liabilities:.2f}',
            'cash': f'{cash:.2f}',
            'loan_outstanding': f'{loan_outstanding:.2f}',
            'outbound_valuation': f'{outbound_valuation:.2f}',
        }

        NavService._persist_nav_record(result)
        return result

    @staticmethod
    def _persist_nav_record(nav_data: dict):
        try:
            NavHistory.objects.create(
                nav_date=date.fromisoformat(nav_data['nav_date']),
                nav_per_unit=nav_data['nav_per_unit'],
                total_units=nav_data['total_units'],
                total_aum=nav_data['total_aum'],
                total_assets=nav_data['total_assets'],
                total_liabilities=nav_data['total_liabilities'],
                cash=nav_data['cash'],
                loan_outstanding=nav_data['loan_outstanding'],
                outbound_valuation=nav_data['outbound_valuation'],
                management_fee_accrued=0,
                performance_fee_accrued=0,
            )
        except Exception as e:
            investment_logger.error(f'NAV persist failed: {e}')

    @staticmethod
    def get_current_nav() -> dict | None:
        latest = NavHistory.objects.filter(is_active=True).order_by('-nav_date').first()
        if not latest:
            return None
        return _model_to_dict(latest)

    @staticmethod
    def issue_units(investor_id: str, amount: str, nav_per_unit: str | None = None) -> dict:
        if nav_per_unit is None:
            current_nav = NavService.get_current_nav()
            nav_per_unit = current_nav['nav_per_unit'] if current_nav else '1.0000'

        amount_float = money_to_float(amount)
        nav_float = money_to_float(nav_per_unit)
        units = round(amount_float / nav_float, 4) if nav_float > 0 else 0.0

        try:
            investor = Investor.objects.get(pk=investor_id)
        except Investor.DoesNotExist:
            return {'error': 'Investor not found'}

        existing = InvestorHolding.objects.filter(investor=investor, is_active=True).first()

        if existing:
            old_units = float(existing.units_held)
            old_cost = float(existing.total_invested)
            new_units = round(old_units + units, 4)
            new_invested = old_cost + amount_float
            new_avg_cost = round(new_invested / new_units, 4) if new_units > 0 else 0.0
            new_value = round(new_units * nav_float, 2)

            existing.units_held = new_units
            existing.avg_cost_per_unit = new_avg_cost
            existing.total_invested = new_invested
            existing.current_value = new_value
            existing.unrealized_pl = round(new_value - new_invested, 2)
            existing.save()
        else:
            new_value = round(units * nav_float, 2)
            InvestorHolding.objects.create(
                investor=investor,
                units_held=units,
                avg_cost_per_unit=nav_float,
                total_invested=amount_float,
                current_value=new_value,
                unrealized_pl=0,
            )

        return {
            'investor_id': investor_id,
            'units_issued': f'{units:.4f}',
            'nav_per_unit': f'{nav_float:.4f}',
            'amount_invested': f'{amount_float:.2f}',
        }

    @staticmethod
    def redeem_units(investor_id: str, units: str, nav_per_unit: str | None = None) -> dict:
        if nav_per_unit is None:
            current_nav = NavService.get_current_nav()
            nav_per_unit = current_nav['nav_per_unit'] if current_nav else '1.0000'

        units_float = money_to_float(units)
        nav_float = money_to_float(nav_per_unit)
        proceeds = round(units_float * nav_float, 2)

        try:
            investor = Investor.objects.get(pk=investor_id)
        except Investor.DoesNotExist:
            return {'error': 'Investor not found'}

        h = InvestorHolding.objects.filter(investor=investor, is_active=True).first()
        if h:
            old_units = float(h.units_held)
            new_units = round(max(old_units - units_float, 0.0), 4)
            avg_cost = float(h.avg_cost_per_unit)
            redeemed_cost = round(units_float * avg_cost, 2)
            new_invested = round(max(float(h.total_invested) - redeemed_cost, 0.0), 2)
            new_value = round(new_units * nav_float, 2)

            h.units_held = new_units
            h.total_invested = new_invested
            h.current_value = new_value
            h.unrealized_pl = round(new_value - new_invested, 2)
            h.save()

        return {
            'investor_id': investor_id,
            'units_redeemed': f'{units_float:.4f}',
            'nav_per_unit': f'{nav_float:.4f}',
            'proceeds': f'{proceeds:.2f}',
        }


# ══════════════════════════════════════════════
# FEE ENGINE
# ══════════════════════════════════════════════

class FeeService:
    """Management and performance fee calculation."""

    @staticmethod
    def get_fee_structure() -> dict:
        fs_obj = FeeStructure.objects.filter(is_active=True).first()
        if fs_obj:
            return _model_to_dict(fs_obj)
        return {
            'management_fee_annual_pct': '2.00',
            'performance_fee_pct': '20.00',
            'hurdle_rate_pct': '5.00',
            'high_water_mark': '0.0000',
            'fee_frequency': 'monthly',
        }

    @staticmethod
    def calculate_management_fee(aum: str, annual_rate_pct: str, days: int) -> str:
        aum_f = money_to_float(aum)
        rate_f = money_to_float(annual_rate_pct) / 100.0
        fee = round(aum_f * (rate_f / 365.0) * days, 2)
        return f'{fee:.2f}'

    @staticmethod
    def calculate_performance_fee(
        current_nav: str, high_water_mark: str,
        total_units: str, perf_fee_pct: str,
    ) -> str:
        nav_f = money_to_float(current_nav)
        hwm_f = money_to_float(high_water_mark)
        units_f = money_to_float(total_units)
        fee_pct_f = money_to_float(perf_fee_pct) / 100.0

        if nav_f <= hwm_f:
            return '0.00'

        excess = nav_f - hwm_f
        fee = round(excess * units_f * fee_pct_f, 2)
        return f'{fee:.2f}'

    @staticmethod
    def accrue_management_fee(nav_date: date) -> dict | None:
        current_nav = NavService.get_current_nav()
        if not current_nav:
            return None

        fee_struct = FeeService.get_fee_structure()
        aum = current_nav.get('total_aum', '0.00')
        annual_rate = fee_struct.get('management_fee_annual_pct', '2.00')

        last_nav = NavService._get_previous_nav(nav_date)
        days = (nav_date - date.fromisoformat(last_nav['nav_date'])).days if last_nav else 1

        mgmt_fee = FeeService.calculate_management_fee(aum, annual_rate, max(days, 1))
        nav_before = money_to_float(current_nav['total_aum'])
        nav_after = round(max(nav_before - money_to_float(mgmt_fee), 0.0), 2)

        try:
            FeeAccrual.objects.create(
                accrual_date=nav_date,
                fee_type='management',
                amount=mgmt_fee,
                nav_before_fee=nav_before,
                nav_after_fee=nav_after,
                is_settled=False,
            )
        except Exception as e:
            investment_logger.error(f'Fee accrual persist failed: {e}')
            return None

        return {
            'fee_type': 'management',
            'amount': mgmt_fee,
            'nav_before_fee': f'{nav_before:.2f}',
            'nav_after_fee': f'{nav_after:.2f}',
        }

    @staticmethod
    def _get_previous_nav(nav_date: date) -> dict | None:
        qs = NavHistory.objects.filter(is_active=True, nav_date__lt=nav_date).order_by('-nav_date')
        record = qs.first()
        return _model_to_dict(record) if record else None


# ══════════════════════════════════════════════
# COMPLIANCE SERVICE
# ══════════════════════════════════════════════

class ComplianceService:
    CONCENTRATION_THRESHOLD = 0.25

    @staticmethod
    def investor_concentration(investor_id: str) -> dict:
        latest_nav = NavHistory.objects.filter(is_active=True).order_by('-nav_date').first()
        total_aum = float(latest_nav.total_aum) if latest_nav else 0.0

        investor_holdings = InvestorHolding.objects.filter(investor__id=investor_id, is_active=True)
        total_holding = sum(float(h.current_value) for h in investor_holdings)

        concentration = (total_holding / total_aum * 100) if total_aum > 0 else 0.0

        return {
            'investor_id': investor_id,
            'holding_value': f'{total_holding:.2f}',
            'total_aum': f'{total_aum:.2f}',
            'concentration_pct': round(concentration, 4),
            'threshold_pct': ComplianceService.CONCENTRATION_THRESHOLD * 100,
            'breached': concentration > ComplianceService.CONCENTRATION_THRESHOLD * 100,
        }

    @staticmethod
    def all_investor_concentrations() -> list[dict]:
        holdings = InvestorHolding.objects.filter(is_active=True).select_related('investor')
        latest_nav = NavHistory.objects.filter(is_active=True).order_by('-nav_date').first()
        total_aum = float(latest_nav.total_aum) if latest_nav else 0.0

        by_investor = {}
        for h in holdings:
            inv_id = str(h.investor_id)
            if inv_id not in by_investor:
                by_investor[inv_id] = {'val': 0.0, 'name': h.investor.name if h.investor else 'Unknown'}
            by_investor[inv_id]['val'] += float(h.current_value)

        results = []
        for inv_id, info in by_investor.items():
            conc = (info['val'] / total_aum * 100) if total_aum > 0 else 0.0
            results.append({
                'investor_id': inv_id,
                'investor_name': info['name'],
                'holding_value': f'{info["val"]:.2f}',
                'concentration_pct': round(conc, 4),
                'threshold_pct': ComplianceService.CONCENTRATION_THRESHOLD * 100,
                'breached': conc > ComplianceService.CONCENTRATION_THRESHOLD * 100,
            })

        results.sort(key=lambda r: r['concentration_pct'], reverse=True)
        return results

    @staticmethod
    def sector_concentration() -> dict:
        loans = Loan.objects.filter(is_active=True)
        total_outstanding = sum(float(l.outstanding_balance) for l in loans)

        by_sector = {}
        for loan in loans:
            sector = loan.sector or 'Unclassified'
            if sector not in by_sector:
                by_sector[sector] = 0.0
            by_sector[sector] += float(loan.outstanding_balance)

        sectors = []
        for sector, val in by_sector.items():
            pct = (val / total_outstanding * 100) if total_outstanding > 0 else 0.0
            sectors.append({
                'sector': sector,
                'outstanding': f'{val:.2f}',
                'concentration_pct': round(pct, 4),
            })

        sectors.sort(key=lambda r: r['concentration_pct'], reverse=True)
        return {
            'total_outstanding': f'{total_outstanding:.2f}',
            'sectors': sectors,
        }

    @staticmethod
    def instrument_concentration() -> dict:
        instruments = FinancialInstrument.objects.filter(is_active=True)
        total_face = sum(float(i.face_value) for i in instruments)

        by_type = {}
        for inst in instruments:
            itype = inst.instrument_type or 'Unknown'
            if itype not in by_type:
                by_type[itype] = 0.0
            by_type[itype] += float(inst.face_value)

        types = []
        for itype, val in by_type.items():
            pct = (val / total_face * 100) if total_face > 0 else 0.0
            types.append({
                'instrument_type': itype,
                'face_value': f'{val:.2f}',
                'concentration_pct': round(pct, 4),
            })

        types.sort(key=lambda r: r['concentration_pct'], reverse=True)
        return {
            'total_face_value': f'{total_face:.2f}',
            'types': types,
        }

    @staticmethod
    def kyc_compliance_report() -> list[dict]:
        investors = Investor.objects.filter(is_active=True)
        today = date.today()
        thirty_days = today + timedelta(days=30)
        report = []

        for inv in investors:
            kyc_status = inv.kyc_status
            kyc_doc_url = inv.kyc_document.url if inv.kyc_document else ''

            is_expired = kyc_status == 'Expired'
            expires_soon = False

            report.append({
                'investor_id': str(inv.id),
                'investor_name': inv.name,
                'kyc_status': kyc_status,
                'kyc_expiry_date': '',
                'kyc_document_url': kyc_doc_url,
                'has_document': bool(inv.kyc_document),
                'is_expired': is_expired,
                'expires_soon': expires_soon,
                'needs_attention': kyc_status in ('Pending', 'Expired', 'Rejected') or is_expired or expires_soon,
            })

        report.sort(key=lambda r: (not r['needs_attention'], r['investor_name']))
        return report


# ══════════════════════════════════════════════
# PERFORMANCE METRICS SERVICE
# ══════════════════════════════════════════════

class PerformanceService:
    """Portfolio performance analytics: TWRR, MWRR, risk metrics, drawdown."""

    @staticmethod
    def time_weighted_return(nav_series: list[dict]) -> float:
        if len(nav_series) < 2:
            return 0.0
        product = 1.0
        prev_nav = None
        for entry in nav_series:
            nav = float(entry.get('nav_per_unit', 0))
            if nav <= 0:
                continue
            if prev_nav is not None and prev_nav > 0:
                r = (nav - prev_nav) / prev_nav
                product *= (1.0 + r)
            prev_nav = nav
        return round(product - 1.0, 6)

    @staticmethod
    def money_weighted_return(cash_flows: list[dict], final_value: float, max_iter: int = 1000) -> float:
        if not cash_flows:
            return 0.0
        total_days = max(cf.get('days_from_start', 0) for cf in cash_flows) + 1

        def npv(rate):
            result = -final_value
            for cf in cash_flows:
                t = cf.get('days_from_start', 0) / total_days if total_days > 0 else 0
                result += cf.get('amount', 0) / ((1 + rate) ** t)
            return result

        def npv_derivative(rate):
            result = 0.0
            for cf in cash_flows:
                t = cf.get('days_from_start', 0) / total_days if total_days > 0 else 0
                if t > 0:
                    result -= t * cf.get('amount', 0) / ((1 + rate) ** (t + 1))
            return result

        rate = 0.1
        for _ in range(max_iter):
            f = npv(rate)
            f_prime = npv_derivative(rate)
            if abs(f_prime) < 1e-12:
                break
            rate_new = rate - f / f_prime
            if abs(rate_new - rate) < 1e-10:
                return round(rate_new, 6)
            rate = rate_new
        return round(rate, 6)

    @staticmethod
    def sharpe_ratio(returns: list[float], risk_free_rate: float = 0.05) -> float:
        if len(returns) < 2:
            return 0.0
        excess_returns = [r - risk_free_rate for r in returns]
        avg_excess = mean(excess_returns)
        sigma = stdev(excess_returns)
        if sigma == 0:
            return 0.0
        return round(avg_excess / sigma, 4)

    @staticmethod
    def sortino_ratio(returns: list[float], risk_free_rate: float = 0.05, target: float = 0.0) -> float:
        if len(returns) < 2:
            return 0.0
        avg_return = mean(returns)
        downside = [r - target for r in returns if r < target]
        if not downside:
            return 0.0
        downside_var = sum(d * d for d in downside) / len(returns)
        downside_sigma = downside_var ** 0.5
        if downside_sigma == 0:
            return 0.0
        return round((avg_return - risk_free_rate) / downside_sigma, 4)

    @staticmethod
    def max_drawdown(nav_series: list[dict]) -> dict:
        if len(nav_series) < 2:
            return {'max_drawdown_pct': 0.0, 'peak_date': '', 'trough_date': ''}
        peak = None
        peak_date = ''
        max_dd = 0.0
        trough_date = ''
        for entry in nav_series:
            nav = float(entry.get('nav_per_unit', 0))
            nav_date_val = entry.get('nav_date', '')
            if nav <= 0:
                continue
            if peak is None or nav > peak:
                peak = nav
                peak_date = nav_date_val
            dd = (peak - nav) / peak
            if dd > max_dd:
                max_dd = dd
                trough_date = nav_date_val
        return {
            'max_drawdown_pct': round(max_dd * 100, 4),
            'peak_date': peak_date,
            'trough_date': trough_date,
        }

    @staticmethod
    def annualized_return(total_return: float, years: float) -> float:
        if years <= 0:
            return 0.0
        if total_return <= -1.0:
            return -1.0
        return round((1.0 + total_return) ** (1.0 / years) - 1.0, 6)

    @staticmethod
    def rolling_return(nav_series: list[dict], window_months: int = 12) -> list[dict]:
        if len(nav_series) < window_months + 1:
            return []
        result = []
        for i in range(window_months, len(nav_series)):
            start_nav = float(nav_series[i - window_months].get('nav_per_unit', 0))
            end_nav = float(nav_series[i].get('nav_per_unit', 0))
            if start_nav > 0:
                r = (end_nav - start_nav) / start_nav
                result.append({
                    'date': nav_series[i].get('nav_date', ''),
                    'return': round(r, 6),
                })
        return result

    @staticmethod
    def volatility(returns: list[float]) -> float:
        if len(returns) < 2:
            return 0.0
        return round(stdev(returns), 6)


# ══════════════════════════════════════════════
# CASH FLOW FORECAST & SCENARIO MODELING
# ══════════════════════════════════════════════

class CashFlowForecastService:
    """Project cash flows, AUM growth, and scenario modeling."""

    @staticmethod
    def forecast_payables(months_ahead: int = 12) -> list[dict]:
        from calendar import monthrange
        today = date.today()
        schedules = LoanSchedule.objects.filter(is_active=True)
        loans = {str(l.id): l for l in Loan.objects.filter(is_active=True)}

        monthly = {}
        for i in range(months_ahead):
            dt = today + relativedelta(months=i)
            key = dt.strftime('%Y-%m')
            monthly[key] = {'month': key, 'projected_inflow': 0.0, 'schedule_count': 0}

        for sch in schedules:
            due = sch.due_date
            status = sch.payment_status
            if status in ('Paid',) or not due:
                continue

            if due < today:
                continue

            loan = loans.get(str(sch.loan_id) if sch.loan_id else '')
            if loan and loan.status not in ('Active',):
                continue

            key = due.strftime('%Y-%m')
            if key in monthly:
                inflow = float(sch.scheduled_principal) + float(sch.scheduled_interest)
                monthly[key]['projected_inflow'] += inflow
                monthly[key]['schedule_count'] += 1

        result = []
        for key in sorted(monthly.keys()):
            m = monthly[key]
            result.append({
                'month': m['month'],
                'projected_inflow': round(m['projected_inflow'], 2),
                'schedule_count': m['schedule_count'],
            })
        return result

    @staticmethod
    def forecast_outbound_calls(months_ahead: int = 12) -> list[dict]:
        today = date.today()
        outbounds = OutboundPlacement.objects.filter(is_active=True, status='Active')

        monthly = {}
        for i in range(months_ahead):
            dt = today + relativedelta(months=i)
            key = dt.strftime('%Y-%m')
            monthly[key] = {'month': key, 'projected_outflow': 0.0, 'call_count': 0}

        for ob in outbounds:
            allocated = float(ob.allocated_capital)
            roi = float(ob.roi_expected_annual)
            placement_date = ob.placement_date

            if not placement_date:
                continue

            start = placement_date

            for i in range(months_ahead):
                dt = today + relativedelta(months=i)
                if dt < start:
                    continue
                key = dt.strftime('%Y-%m')
                if key in monthly:
                    call = allocated / months_ahead
                    monthly[key]['projected_outflow'] += call
                    monthly[key]['call_count'] += 1

        result = []
        for key in sorted(monthly.keys()):
            m = monthly[key]
            result.append({
                'month': m['month'],
                'projected_outflow': round(m['projected_outflow'], 2),
                'call_count': m['call_count'],
            })
        return result

    @staticmethod
    def forecast_nav_growth(
        months_ahead: int = 12,
        expected_return_pct: float = 10.0,
        expected_inflows: list[dict] | None = None,
    ) -> list[dict]:
        today = date.today()
        r_monthly = expected_return_pct / 100.0 / 12.0

        nav_records = NavHistory.objects.filter(is_active=True).order_by('nav_date')
        if not nav_records.exists():
            return []

        latest = nav_records.last()
        aum = float(latest.total_aum)
        nav_per_unit = float(latest.nav_per_unit)
        total_units = float(latest.total_units)

        inflow_map = {}
        if expected_inflows:
            for item in expected_inflows:
                inflow_map[item.get('month', '')] = money_to_float(item.get('amount', '0.00'))

        fee_struct = FeeStructure.objects.filter(is_active=True).first()
        mgmt_fee_annual = float(fee_struct.management_fee_annual_pct) if fee_struct else 2.0
        mgmt_fee_monthly = mgmt_fee_annual / 100.0 / 12.0

        result = []
        for i in range(months_ahead):
            dt = today + relativedelta(months=i + 1)
            key = dt.strftime('%Y-%m')
            net_inflow = inflow_map.get(key, 0.0)

            investment_return = aum * r_monthly
            fee = aum * mgmt_fee_monthly
            aum = aum + investment_return + net_inflow - fee
            aum = max(aum, 0.0)

            if total_units > 0:
                nav_per_unit = aum / total_units

            result.append({
                'month': key,
                'projected_aum': round(aum, 2),
                'nav_per_unit': round(nav_per_unit, 4),
                'investment_return': round(investment_return, 2),
                'fee_deduction': round(fee, 2),
                'net_inflow': round(net_inflow, 2),
            })
        return result

    @staticmethod
    def what_if_default_rate(
        base_default_rate: float = 0.02,
        stress_default_rate: float = 0.10,
    ) -> dict:
        active_loans = Loan.objects.filter(is_active=True, status='Active')
        total_outstanding = sum(float(l.outstanding_balance) for l in active_loans)

        latest_nav = NavHistory.objects.filter(is_active=True).order_by('-nav_date').first()
        current_aum = float(latest_nav.total_aum) if latest_nav else 0.0

        base_loss = total_outstanding * base_default_rate
        stress_loss = total_outstanding * stress_default_rate

        base_aum = max(current_aum - base_loss, 0.0)
        stress_aum = max(current_aum - stress_loss, 0.0)

        return {
            'current_aum': f'{current_aum:.2f}',
            'total_outstanding_loans': f'{total_outstanding:.2f}',
            'active_loans_count': active_loans.count(),
            'base_default_rate': base_default_rate,
            'stress_default_rate': stress_default_rate,
            'base_loss': f'{base_loss:.2f}',
            'stress_loss': f'{stress_loss:.2f}',
            'base_aum_after': f'{base_aum:.2f}',
            'stress_aum_after': f'{stress_aum:.2f}',
            'base_aum_impact_pct': round(-base_default_rate * 100, 2),
            'stress_aum_impact_pct': round(-stress_default_rate * 100, 2),
        }


# ══════════════════════════════════════════════
# AUDIT HELPERS (backward compat — ignored)
# ══════════════════════════════════════════════

def audit_create(user) -> dict:
    return {'created_at': timezone.now(), 'updated_at': timezone.now()}


def audit_update(user) -> dict:
    return {'updated_at': timezone.now()}
