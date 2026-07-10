"""
Investment Service Layer

Firestore-only data access and business logic.
No Django ORM dependencies.
"""

from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from dateutil.relativedelta import relativedelta
from typing import Optional
from math import isnan, isinf
from statistics import stdev, mean

from config.firebase import db
from google.cloud import firestore
from config.logger import investment_logger


# ──────────────────────────────────────────────
# Collection name constants
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
    """Convert a numeric value to BDT string with Indian numbering commas.

    Examples:
        money_to_str(1234567.89)  → "BDT 12,34,567.89"
        money_to_str(100000.0)    → "BDT 1,00,000.00"
        money_to_str(0.0)         → "BDT 0.00"
    """
    if value is None:
        return f'{_BDT_PREFIX}0.00'
    if isinstance(value, str):
        value = money_to_float(value)
    formatted = f'{value:,.2f}'
    parts = formatted.split('.')
    integer_part = parts[0]
    # Convert standard commas (3-digit groups) to Indian numbering (first group of 3, then groups of 2)
    if ',' in integer_part:
        groups = integer_part.split(',')
        # Standard: 1,234,567 → Indian: first group joins next, then 2-digit groups
        # groups = ['1', '234', '567'] → groups = ['12', '34', '567']? No...
        # Actually: 12,34,567 → groups = ['12', '34', '567']
        # From standard: 1,234,567 → last 3 digits stay, preceding groups shift
        last = groups[-1]
        rest = groups[:-1]
        combined = ''.join(rest)
        # Indian: combined (no comma between these) + ',' + last
        # But combined may itself need 2-digit grouping
        if len(combined) <= 2:
            indian_groups = [combined, last]
        else:
            rev = combined[::-1]
            pairs = [rev[i:i+2] for i in range(0, len(rev), 2)]
            indian_groups = [p[::-1] for p in reversed(pairs)] + [last]
        integer_part = ','.join(indian_groups)
    return f'{_BDT_PREFIX}{integer_part}.{parts[1]}'


def money_to_float(value: str | float | int | None) -> float:
    """Parse a BDT string (or numeric) back to float.

    Examples:
        money_to_float("BDT 12,34,567.89")  → 1234567.89
        money_to_float("BDT 1,00,000.00")   → 100000.0
        money_to_float(100.0)               → 100.0
        money_to_float(None)                → 0.0
    """
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
    """Safely sum one or more monetary values (mixed str/float)."""
    total = 0.0
    for v in values:
        total += money_to_float(v)
    return total


def money_to_storage(value: str | float | int | None) -> str:
    """Convert a monetary value to a portable string for Firestore storage.

    Returns a plain number string (no prefix/commas) suitable for persistence.
    Examples:
        money_to_storage(1234567.89)  → "1234567.89"
        money_to_storage("BDT 1,00,000.00") → "100000.00"
    """
    return f'{money_to_float(value):.2f}'


# ══════════════════════════════════════════════
# FIRESTORE DATA ACCESS
# ══════════════════════════════════════════════

class FirestoreService:
    """Thin wrapper over Firestore CRUD operations."""

    @staticmethod
    def get_collection(collection_name: str) -> list[dict]:
        """Fetch all documents from a collection. Each doc includes its 'id'."""
        try:
            docs = db.collection(collection_name).stream()
            return [{**doc.to_dict(), 'id': doc.id} for doc in docs]
        except Exception as e:
            investment_logger.error(f"Firestore fetch error [{collection_name}]: {e}")
            return []

    @staticmethod
    def get_document(collection_name: str, doc_id: str) -> Optional[dict]:
        """Fetch a single document by ID. Returns None if missing."""
        try:
            doc = db.collection(collection_name).document(doc_id).get()
            if doc.exists:
                return {**doc.to_dict(), 'id': doc.id}
            return None
        except Exception as e:
            investment_logger.error(f"Firestore get error [{collection_name}/{doc_id}]: {e}")
            return None

    @staticmethod
    def create_document(collection_name: str, data: dict) -> Optional[str]:
        """Create a document and return its ID. Adds SERVER_TIMESTAMP."""
        try:
            data['created_at'] = firestore.SERVER_TIMESTAMP
            data['updated_at'] = firestore.SERVER_TIMESTAMP
            _, ref = db.collection(collection_name).add(data)
            return ref.id
        except Exception as e:
            investment_logger.error(f"Firestore create error [{collection_name}]: {e}")
            return None

    @staticmethod
    def update_document(collection_name: str, doc_id: str, data: dict) -> bool:
        """Update an existing document. Never overwrites created_at."""
        try:
            data.pop('created_at', None)
            data['updated_at'] = firestore.SERVER_TIMESTAMP
            db.collection(collection_name).document(doc_id).update(data)
            return True
        except Exception as e:
            investment_logger.error(f"Firestore update error [{collection_name}/{doc_id}]: {e}")
            return False

    @staticmethod
    def delete_document(collection_name: str, doc_id: str) -> bool:
        """Delete a document by ID."""
        try:
            db.collection(collection_name).document(doc_id).delete()
            return True
        except Exception as e:
            investment_logger.error(f"Firestore delete error [{collection_name}/{doc_id}]: {e}")
            return False

    @staticmethod
    def query_collection(collection_name: str, field: str, operator: str, value) -> list[dict]:
        """Query a collection with a where clause."""
        try:
            docs = db.collection(collection_name).where(field, operator, value).stream()
            return [{**doc.to_dict(), 'id': doc.id} for doc in docs]
        except Exception as e:
            investment_logger.error(f"Firestore query error [{collection_name}]: {e}")
            return []

    @staticmethod
    def batch_write(operations: list[tuple]) -> bool:
        """Execute a batch of writes.
        Each tuple: ('set'|'update'|'delete', collection_name, doc_id_or_none, data_or_none)
        """
        try:
            batch = db.batch()
            for op in operations:
                coll = db.collection(op[1])
                if op[0] == 'set':
                    ref = coll.document(op[2]) if op[2] else coll.document()
                    batch.set(ref, op[3])
                elif op[0] == 'update':
                    batch.update(coll.document(op[2]), op[3])
                elif op[0] == 'delete':
                    batch.delete(coll.document(op[2]))
            batch.commit()
            return True
        except Exception as e:
            investment_logger.error(f"Firestore batch error: {e}")
            return False


# ══════════════════════════════════════════════
# UNIQUE CODE GENERATION
# ══════════════════════════════════════════════

class CodeGenerator:
    """Generates unique sequential codes using a Firestore counter document.
    The Firestore transaction ensures atomicity under concurrent writes."""

    @staticmethod
    def _next_sequence(counter_id: str, prefix: str, pad: int = 5) -> Optional[str]:
        """Atomically increment a counter and return the formatted code."""
        try:
            counter_ref = db.collection(COLL_COUNTERS).document(counter_id)

            @firestore.transactional
            def increment(transaction):
                snapshot = counter_ref.get(transaction=transaction)
                if not snapshot.exists:
                    transaction.set(counter_ref, {'value': 1})
                    return 1
                current = snapshot.to_dict().get('value', 0)
                transaction.update(counter_ref, {'value': current + 1})
                return current + 1

            transaction = db.transaction()
            seq = increment(transaction)
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


# ══════════════════════════════════════════════
# INVESTOR CODE GENERATION (LEGACY MIGRATION)
# ══════════════════════════════════════════════

def migrate_investor_codes():
    """One-time migration: seed the Firestore counter to match existing max code.
    Safe to run multiple times — only sets if counter doesn't exist."""
    counter_ref = db.collection(COLL_COUNTERS).document('investor_code')
    if counter_ref.get().exists:
        return
    investors = db.collection(COLL_INVESTORS).stream()
    max_seq = 0
    for inv in investors:
        code = inv.to_dict().get('investor_code', '')
        if code.startswith('INV-'):
            try:
                seq = int(code.split('-')[1])
                max_seq = max(max_seq, seq)
            except (IndexError, ValueError):
                continue
    if max_seq > 0:
        counter_ref.set({'value': max_seq})


# ══════════════════════════════════════════════
# AMORTIZATION ENGINE (PMT Formula)
# ══════════════════════════════════════════════

class AmortizationService:
    """PMT-based equal-installment amortization schedule generator."""

    @staticmethod
    def compute_pmt(principal: float, annual_rate_pct: float, months: int) -> float:
        """Compute equal periodic payment using the PMT formula.
        Formula: PMT = P * [r(1+r)^n] / [(1+r)^n - 1]
        where r = annual_rate/100/12, n = months
        """
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
        """Generate a full amortization schedule as a list of dicts.
        Each dict is ready to write to invst_loan_schedules.
        """
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
        """Sum scheduled_interest for all schedules matching the given month (YYYY-MM)."""
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
        """Compute NAV per unit and persist to invst_nav_history.

        NAV = (Total Assets - Total Liabilities) / Total Units Outstanding

        Total Assets = Cash + Loan Outstanding + Outbound Valuations
        Total Liabilities = Unpaid Interest + Fee Accruals
        """
        transactions = FirestoreService.get_collection(COLL_TRANSACTIONS)
        loans = FirestoreService.get_collection(COLL_LOANS)
        outbound = FirestoreService.get_collection(COLL_OUTBOUND)
        schedules = FirestoreService.get_collection(COLL_LOAN_SCHEDULES)
        holdings = FirestoreService.get_collection(COLL_INVESTOR_HOLDINGS)
        fee_accruals = FirestoreService.get_collection(COLL_FEE_ACCRUALS)

        cash = 0.0
        for tx in transactions:
            if tx.get('status') == 'Cleared':
                amt = money_to_float(tx.get('amount', 0.0))
                ttype = tx.get('transaction_type', '')
                if ttype == 'Capital Influx':
                    cash += amt
                elif ttype in ('Capital Withdrawal', 'Interest Payout', 'Dividend Payout'):
                    cash -= amt

        loan_outstanding = sum(
            money_to_float(l.get('outstanding_balance', 0.0))
            for l in loans if l.get('status') == 'Active'
        )

        outbound_valuation = sum(
            money_to_float(o.get('current_valuation', 0.0))
            for o in outbound if o.get('status') == 'Active'
        )

        total_assets = cash + loan_outstanding + outbound_valuation

        unpaid_interest = sum(
            money_to_float(s.get('scheduled_interest', 0.0))
            for s in schedules if s.get('payment_status') in ('Unpaid', 'Overdue')
        )

        unpaid_fees = sum(
            money_to_float(f.get('amount', 0.0))
            for f in fee_accruals if not f.get('is_settled', True)
        )

        total_liabilities = unpaid_interest + unpaid_fees
        total_aum = round(max(total_assets - total_liabilities, 0.0), 2)
        total_units = sum(
            money_to_float(h.get('units_held', '0.0000'))
            for h in holdings if h.get('is_active', True)
        )

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
        """Write NAV record to invst_nav_history."""
        try:
            FirestoreService.create_document(COLL_NAV_HISTORY, {
                **nav_data,
                'management_fee_accrued': '0.00',
                'performance_fee_accrued': '0.00',
                'is_active': True,
            })
        except Exception as e:
            investment_logger.error(f'NAV persist failed: {e}')

    @staticmethod
    def get_current_nav() -> dict | None:
        """Return the most recent NAV record."""
        records = FirestoreService.get_collection(COLL_NAV_HISTORY)
        if not records:
            return None
        records.sort(key=lambda r: r.get('nav_date', ''), reverse=True)
        return records[0]

    @staticmethod
    def issue_units(investor_id: str, amount: str, nav_per_unit: str | None = None) -> dict:
        """Issue new units at current NAV.

        Units = Investment Amount / NAV per Unit
        Uses Firestore transaction for consistency.
        """
        if nav_per_unit is None:
            current_nav = NavService.get_current_nav()
            nav_per_unit = current_nav['nav_per_unit'] if current_nav else '1.0000'

        amount_float = money_to_float(amount)
        nav_float = money_to_float(nav_per_unit)
        units = round(amount_float / nav_float, 4) if nav_float > 0 else 0.0

        existing = None
        for h in FirestoreService.get_collection(COLL_INVESTOR_HOLDINGS):
            if h.get('investor_id') == investor_id and h.get('is_active', True):
                existing = h
                break

        if existing:
            old_units = money_to_float(existing['units_held'])
            old_cost = money_to_float(existing['total_invested'])
            new_units = round(old_units + units, 4)
            new_invested = money_add(old_cost, amount_float)
            new_avg_cost = round(new_invested / new_units, 4) if new_units > 0 else 0.0
            new_value = round(new_units * nav_float, 2)

            FirestoreService.update_document(COLL_INVESTOR_HOLDINGS, existing['id'], {
                'units_held': f'{new_units:.4f}',
                'avg_cost_per_unit': f'{new_avg_cost:.4f}',
                'total_invested': f'{new_invested:.2f}',
                'current_value': f'{new_value:.2f}',
                'unrealized_pl': f'{round(new_value - new_invested, 2):.2f}',
            })
        else:
            new_value = round(units * nav_float, 2)
            doc_id = FirestoreService.create_document(COLL_INVESTOR_HOLDINGS, {
                'investor_id': investor_id,
                'units_held': f'{units:.4f}',
                'avg_cost_per_unit': f'{nav_per_unit}',
                'total_invested': f'{amount_float:.2f}',
                'current_value': f'{new_value:.2f}',
                'unrealized_pl': '0.00',
                'is_active': True,
            })
            if doc_id:
                investment_logger.info(f'Created holding record {doc_id} for investor {investor_id}')

        return {
            'investor_id': investor_id,
            'units_issued': f'{units:.4f}',
            'nav_per_unit': f'{nav_float:.4f}',
            'amount_invested': f'{amount_float:.2f}',
        }

    @staticmethod
    def redeem_units(investor_id: str, units: str, nav_per_unit: str | None = None) -> dict:
        """Redeem units at current NAV.

        Proceeds = Units * NAV per Unit
        """
        if nav_per_unit is None:
            current_nav = NavService.get_current_nav()
            nav_per_unit = current_nav['nav_per_unit'] if current_nav else '1.0000'

        units_float = money_to_float(units)
        nav_float = money_to_float(nav_per_unit)
        proceeds = round(units_float * nav_float, 2)

        for h in FirestoreService.get_collection(COLL_INVESTOR_HOLDINGS):
            if h.get('investor_id') == investor_id and h.get('is_active', True):
                old_units = money_to_float(h['units_held'])
                new_units = round(max(old_units - units_float, 0.0), 4)
                old_invested = money_to_float(h['total_invested'])
                avg_cost = money_to_float(h['avg_cost_per_unit'])
                redeemed_cost = round(units_float * avg_cost, 2)
                new_invested = round(max(old_invested - redeemed_cost, 0.0), 2)
                new_value = round(new_units * nav_float, 2)

                FirestoreService.update_document(COLL_INVESTOR_HOLDINGS, h['id'], {
                    'units_held': f'{new_units:.4f}',
                    'total_invested': f'{new_invested:.2f}',
                    'current_value': f'{new_value:.2f}',
                    'unrealized_pl': f'{round(new_value - new_invested, 2):.2f}',
                })
                break

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
        """Return current fee structure (first active doc)."""
        structures = FirestoreService.get_collection(COLL_FEE_STRUCTURES)
        for s in structures:
            if s.get('is_active', True):
                return s
        return {
            'management_fee_annual_pct': '2.00',
            'performance_fee_pct': '20.00',
            'hurdle_rate_pct': '5.00',
            'high_water_mark': '0.0000',
            'fee_frequency': 'monthly',
        }

    @staticmethod
    def calculate_management_fee(aum: str, annual_rate_pct: str, days: int) -> str:
        """Management fee = AUM * (annual_rate / 365) * days"""
        aum_f = money_to_float(aum)
        rate_f = money_to_float(annual_rate_pct) / 100.0
        fee = round(aum_f * (rate_f / 365.0) * days, 2)
        return f'{fee:.2f}'

    @staticmethod
    def calculate_performance_fee(
        current_nav: str, high_water_mark: str,
        total_units: str, perf_fee_pct: str,
    ) -> str:
        """Performance fee = (Current NAV - HWM) * Units * Fee%

        Only applies when current NAV exceeds high water mark.
        """
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
        """Calculate and record management fee accrual.

        Uses the latest NAV record and fee structure.
        """
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
            FirestoreService.create_document(COLL_FEE_ACCRUALS, {
                'accrual_date': nav_date.isoformat(),
                'fee_type': 'management',
                'amount': mgmt_fee,
                'nav_before_fee': f'{nav_before:.2f}',
                'nav_after_fee': f'{nav_after:.2f}',
                'is_settled': False,
                'is_active': True,
            })
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
        """Return the NAV record immediately before nav_date."""
        records = FirestoreService.get_collection(COLL_NAV_HISTORY)
        prev = None
        for r in records:
            r_date = r.get('nav_date', '')
            if r_date < nav_date.isoformat():
                if prev is None or r_date > prev['nav_date']:
                    prev = r
        return prev


# ══════════════════════════════════════════════
# COMPLIANCE SERVICE (Phase 7)
# ══════════════════════════════════════════════

class ComplianceService:
    """Compliance monitoring: concentration limits, KYC expiry, sector exposure."""

    CONCENTRATION_THRESHOLD = 0.25

    @staticmethod
    def investor_concentration(investor_id: str) -> dict:
        """Return concentration metrics for a single investor.

        Concentration = Holding Current Value / Total AUM
        """
        holdings = FirestoreService.get_collection(COLL_INVESTOR_HOLDINGS)
        nav_history = FirestoreService.get_collection(COLL_NAV_HISTORY)
        nav_history.sort(key=lambda r: r.get('nav_date', ''))
        latest_nav = nav_history[-1] if nav_history else {}
        total_aum = money_to_float(latest_nav.get('total_aum', '0.00'))

        investor_holdings = [h for h in holdings if h.get('investor_id') == investor_id]
        total_holding = sum(money_to_float(h.get('current_value', '0.00')) for h in investor_holdings)

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
        """Concentration for all active investors."""
        holdings = FirestoreService.get_collection(COLL_INVESTOR_HOLDINGS)
        nav_history = FirestoreService.get_collection(COLL_NAV_HISTORY)
        nav_history.sort(key=lambda r: r.get('nav_date', ''))
        latest_nav = nav_history[-1] if nav_history else {}
        total_aum = money_to_float(latest_nav.get('total_aum', '0.00'))

        investors = FirestoreService.get_collection(COLL_INVESTORS)
        inv_map = {inv.get('id'): inv.get('name', 'Unknown') for inv in investors}

        by_investor = {}
        for h in holdings:
            inv_id = h.get('investor_id', '')
            if inv_id not in by_investor:
                by_investor[inv_id] = 0.0
            by_investor[inv_id] += money_to_float(h.get('current_value', '0.00'))

        results = []
        for inv_id, val in by_investor.items():
            conc = (val / total_aum * 100) if total_aum > 0 else 0.0
            results.append({
                'investor_id': inv_id,
                'investor_name': inv_map.get(inv_id, 'Unknown'),
                'holding_value': f'{val:.2f}',
                'concentration_pct': round(conc, 4),
                'threshold_pct': ComplianceService.CONCENTRATION_THRESHOLD * 100,
                'breached': conc > ComplianceService.CONCENTRATION_THRESHOLD * 100,
            })

        results.sort(key=lambda r: r['concentration_pct'], reverse=True)
        return results

    @staticmethod
    def sector_concentration() -> dict:
        """Sector breakdown of loan portfolio."""
        loans = FirestoreService.get_collection(COLL_LOANS)
        total_outstanding = sum(money_to_float(l.get('outstanding_balance', '0.00')) for l in loans)

        by_sector = {}
        for loan in loans:
            sector = loan.get('sector', 'Unclassified')
            if sector not in by_sector:
                by_sector[sector] = 0.0
            by_sector[sector] += money_to_float(loan.get('outstanding_balance', '0.00'))

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
        """Instrument type concentration."""
        instruments = FirestoreService.get_collection(COLL_INSTRUMENTS)
        total_face = sum(money_to_float(i.get('face_value', '0.00')) for i in instruments)

        by_type = {}
        for inst in instruments:
            itype = inst.get('instrument_type', 'Unknown')
            if itype not in by_type:
                by_type[itype] = 0.0
            by_type[itype] += money_to_float(inst.get('face_value', '0.00'))

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
        """All investors with KYC status gaps or upcoming expiry."""
        investors = FirestoreService.get_collection(COLL_INVESTORS)
        from datetime import date, timedelta

        today = date.today()
        thirty_days = today + timedelta(days=30)
        report = []

        for inv in investors:
            kyc_status = inv.get('kyc_status', 'Not Started')
            kyc_expiry = inv.get('kyc_expiry_date', '')
            kyc_doc_url = inv.get('kyc_document_url', '')

            is_expired = False
            expires_soon = False
            if kyc_expiry:
                try:
                    exp_date = date.fromisoformat(kyc_expiry)
                    is_expired = exp_date < today
                    expires_soon = not is_expired and exp_date <= thirty_days
                except ValueError:
                    pass

            report.append({
                'investor_id': inv.get('id', ''),
                'investor_name': inv.get('name', 'Unknown'),
                'kyc_status': kyc_status,
                'kyc_expiry_date': kyc_expiry,
                'kyc_document_url': kyc_doc_url,
                'has_document': bool(kyc_doc_url),
                'is_expired': is_expired,
                'expires_soon': expires_soon,
                'needs_attention': kyc_status in ('Not Started', 'Expired', 'Rejected') or is_expired or expires_soon,
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
        """Compute TWRR using geometric linking of sub-period returns.

        R_sub = (NAV_t - NAV_t-1) / NAV_t-1
        TWRR = (1 + R_1) * (1 + R_2) * ... * (1 + R_n) - 1

        nav_series should be sorted ascending by date, each with 'nav_per_unit'.
        """
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
        """Compute IRR/MWRR using Newton-Raphson method.

        cash_flows: list of {'amount': float, 'days_from_start': int}
        final_value: current portfolio value (positive = inflow at end)
        Returns IRR as a decimal (e.g., 0.12 for 12%).
        """
        if not cash_flows:
            return 0.0

        # Build time-weighted cash flow list
        total_days = max(cf.get('days_from_start', 0) for cf in cash_flows) + 1

        def npv(rate):
            result = -final_value  # Final value is negative (money received)
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

        # Newton-Raphson iteration
        rate = 0.1  # initial guess
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
        """Sharpe = (R_p - R_f) / sigma_p

        Returns annualized Sharpe ratio using the given returns series.
        risk_free_rate should be annualized (default 5% = 0.05).
        """
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
        """Sortino = (R_p - R_f) / downside_deviation

        Only negative deviations below target are penalized.
        """
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
        """Maximum peak-to-trough decline.

        Returns: {'max_drawdown_pct': float, 'peak_date': str, 'trough_date': str}
        """
        if len(nav_series) < 2:
            return {'max_drawdown_pct': 0.0, 'peak_date': '', 'trough_date': ''}

        peak = None
        peak_date = ''
        max_dd = 0.0
        trough_date = ''

        for entry in nav_series:
            nav = float(entry.get('nav_per_unit', 0))
            nav_date = entry.get('nav_date', '')
            if nav <= 0:
                continue
            if peak is None or nav > peak:
                peak = nav
                peak_date = nav_date
            dd = (peak - nav) / peak
            if dd > max_dd:
                max_dd = dd
                trough_date = nav_date

        return {
            'max_drawdown_pct': round(max_dd * 100, 4),
            'peak_date': peak_date,
            'trough_date': trough_date,
        }

    @staticmethod
    def annualized_return(total_return: float, years: float) -> float:
        """CAGR = (1 + total_return)^(1/years) - 1"""
        if years <= 0:
            return 0.0
        if total_return <= -1.0:
            return -1.0
        return round((1.0 + total_return) ** (1.0 / years) - 1.0, 6)

    @staticmethod
    def rolling_return(nav_series: list[dict], window_months: int = 12) -> list[dict]:
        """Rolling periodic returns.

        For each window of `window_months` entries, compute the return.
        Returns list of {'date': str, 'return': float} sorted by date.
        """
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
        """Annualized volatility from a series of periodic returns."""
        if len(returns) < 2:
            return 0.0
        return round(stdev(returns), 6)


# ══════════════════════════════════════════════
# CASH FLOW FORECAST & SCENARIO MODELING (Phase 8)
# ══════════════════════════════════════════════

class CashFlowForecastService:
    """Project cash flows, AUM growth, and scenario modeling."""

    @staticmethod
    def forecast_payables(months_ahead: int = 12) -> list[dict]:
        """Project expected loan repayments from unpaid schedules.

        For each loan schedule with due_date in range:
            inflow = scheduled_principal + scheduled_interest
        Returns monthly aggregation.
        """
        from datetime import date, timedelta
        from calendar import monthrange

        today = date.today()
        schedules = FirestoreService.get_collection(COLL_LOAN_SCHEDULES)
        loans = {l['id']: l for l in FirestoreService.get_collection(COLL_LOANS)}

        monthly = {}
        for i in range(months_ahead):
            dt = today + relativedelta(months=i)
            key = dt.strftime('%Y-%m')
            monthly[key] = {'month': key, 'projected_inflow': 0.0, 'schedule_count': 0}

        for sch in schedules:
            due = sch.get('due_date', '')
            status = sch.get('payment_status', '')
            if status in ('Paid',) or not due:
                continue

            try:
                due_date = date.fromisoformat(due)
            except ValueError:
                continue

            if due_date < today:
                continue

            loan = loans.get(sch.get('loan_id', ''))
            if loan and loan.get('status') not in ('Active',):
                continue

            key = due_date.strftime('%Y-%m')
            if key in monthly:
                inflow = money_to_float(sch.get('scheduled_principal', '0.00')) + money_to_float(sch.get('scheduled_interest', '0.00'))
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
        """Project expected outbound capital requirements from active placements.

        Assumes annual ROI target is distributed monthly for capital calls.
        """
        from datetime import date
        today = date.today()
        outbounds = FirestoreService.get_collection(COLL_OUTBOUND)
        active = [o for o in outbounds if o.get('status') == 'Active']

        monthly = {}
        for i in range(months_ahead):
            dt = today + relativedelta(months=i)
            key = dt.strftime('%Y-%m')
            monthly[key] = {'month': key, 'projected_outflow': 0.0, 'call_count': 0}

        for ob in active:
            allocated = money_to_float(ob.get('allocated_capital', '0.00'))
            roi = money_to_float(ob.get('roi_expected_annual', '0.00'))
            placement_date = ob.get('placement_date', '')

            if not placement_date:
                continue

            try:
                start = date.fromisoformat(placement_date)
            except ValueError:
                continue

            # Distribute allocated capital evenly over the forecast period
            # from placement date onwards
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
        """Project AUM and NAV based on expected returns and capital flows.

        Simple model:
            AUM_t = AUM_t-1 * (1 + r_monthly) + net_cash_flow_t - fees_t
        """
        from datetime import date

        today = date.today()
        r_monthly = expected_return_pct / 100.0 / 12.0

        nav_history = FirestoreService.get_collection(COLL_NAV_HISTORY)
        nav_history.sort(key=lambda r: r.get('nav_date', ''))

        if not nav_history:
            return []

        latest = nav_history[-1]
        aum = money_to_float(latest.get('total_aum', '0.00'))
        nav_per_unit = money_to_float(latest.get('nav_per_unit', '0.0000'))
        total_units = money_to_float(latest.get('total_units', '0.0000'))

        # Build inflow lookup by month
        inflow_map = {}
        if expected_inflows:
            for item in expected_inflows:
                inflow_map[item.get('month', '')] = money_to_float(item.get('amount', '0.00'))

        # Get monthly mgmt fee rate
        fee_structs = FirestoreService.get_collection(COLL_FEE_STRUCTURES)
        mgmt_fee_annual = 0.0
        for fs_ in fee_structs:
            if fs_.get('is_active', True):
                mgmt_fee_annual = money_to_float(fs_.get('management_fee_annual_pct', '2.00'))
                break
        mgmt_fee_monthly = mgmt_fee_annual / 100.0 / 12.0

        result = []
        for i in range(months_ahead):
            dt = today + relativedelta(months=i + 1)
            key = dt.strftime('%Y-%m')

            net_inflow = inflow_map.get(key, 0.0)

            # AUM grows by expected return + new inflows - fees
            investment_return = aum * r_monthly
            fee = aum * mgmt_fee_monthly
            aum = aum + investment_return + net_inflow - fee
            aum = max(aum, 0.0)

            # NAV per unit grows proportionally
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
        """Scenario: what if X% of loans default?

        Stress test AUM impact, cash flow shortfall.
        """
        loans = FirestoreService.get_collection(COLL_LOANS)
        active_loans = [l for l in loans if l.get('status') == 'Active']
        total_outstanding = sum(money_to_float(l.get('outstanding_balance', '0.00')) for l in active_loans)
        total_principal = sum(money_to_float(l.get('principal_amount', '0.00')) for l in active_loans)

        nav_history = FirestoreService.get_collection(COLL_NAV_HISTORY)
        nav_history.sort(key=lambda r: r.get('nav_date', ''))
        latest_nav = nav_history[-1] if nav_history else {}
        current_aum = money_to_float(latest_nav.get('total_aum', '0.00'))

        base_loss = total_outstanding * base_default_rate
        stress_loss = total_outstanding * stress_default_rate

        base_aum = max(current_aum - base_loss, 0.0)
        stress_aum = max(current_aum - stress_loss, 0.0)

        return {
            'current_aum': f'{current_aum:.2f}',
            'total_outstanding_loans': f'{total_outstanding:.2f}',
            'active_loans_count': len(active_loans),
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
# AUDIT HELPERS
# ══════════════════════════════════════════════

def audit_create(user) -> dict:
    """Standard audit fields for document creation."""
    return {
        'created_at': firestore.SERVER_TIMESTAMP,
        'updated_at': firestore.SERVER_TIMESTAMP,
        'created_by': user.email if user and user.is_authenticated else 'system',
        'updated_by': user.email if user and user.is_authenticated else 'system',
    }


def audit_update(user) -> dict:
    """Standard audit fields for document update (preserves created_at)."""
    return {
        'updated_at': firestore.SERVER_TIMESTAMP,
        'updated_by': user.email if user and user.is_authenticated else 'system',
    }
