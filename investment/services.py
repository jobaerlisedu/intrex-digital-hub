"""
Investment Service Layer

Firestore-only data access and business logic.
No Django ORM dependencies.
"""

from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from dateutil.relativedelta import relativedelta
from typing import Optional

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
COLL_COUNTERS = 'system_counters'


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
                'scheduled_principal': round(principal_part, 2),
                'scheduled_interest': round(interest, 2),
                'paid_amount': 0.0,
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
