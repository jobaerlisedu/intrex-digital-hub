"""
Import all data from Firestore collections into MySQL via Django ORM.

Usage:
    python manage.py import_firestore

Requires FIREBASE_CREDENTIALS_JSON or firebase-credentials.json to be available
for reading the source data. The destination is the Django-configured database.
"""
import json
import uuid
from decimal import Decimal
from datetime import date, datetime

from django.core.management.base import BaseCommand
from django.db import transaction as db_transaction
from config.logger import investment_logger

MODEL_ORDER = [
    'invst_investors',
    'invst_transactions',
    'invst_loans',
    'invst_loan_schedules',
    'invst_outbound_placements',
    'invst_financial_instruments',
    'invst_instrument_prices',
    'invst_pl_ledger',
    'invst_nav_history',
    'invst_investor_holdings',
    'invst_fee_structures',
    'invst_fee_accruals',
    'invst_currency_config',
    'invst_fx_rates',
    'invst_counters',
]

MODEL_MAP = {
    'invst_investors': 'Investor',
    'invst_transactions': 'Transaction',
    'invst_loans': 'Loan',
    'invst_loan_schedules': 'LoanSchedule',
    'invst_outbound_placements': 'OutboundPlacement',
    'invst_financial_instruments': 'FinancialInstrument',
    'invst_instrument_prices': 'InstrumentPrice',
    'invst_pl_ledger': 'PLLedger',
    'invst_nav_history': 'NavHistory',
    'invst_investor_holdings': 'InvestorHolding',
    'invst_fee_structures': 'FeeStructure',
    'invst_fee_accruals': 'FeeAccrual',
    'invst_currency_config': 'CurrencyConfig',
    'invst_fx_rates': 'FxRate',
    'invst_counters': 'Sequence',
}


def _parse_value(field, raw):
    """Parse a Firestore field value into the Python type expected by the Django model field."""
    if raw is None:
        return None
    ft = field.get_internal_type()
    if ft in ('DecimalField',):
        try:
            return Decimal(str(raw))
        except Exception:
            return Decimal('0')
    if ft in ('DateField',):
        if isinstance(raw, datetime):
            return raw.date()
        if isinstance(raw, date):
            return raw
        try:
            return date.fromisoformat(str(raw)[:10])
        except Exception:
            return None
    if ft in ('DateTimeField',):
        if isinstance(raw, datetime):
            return raw
        try:
            return datetime.fromisoformat(str(raw))
        except Exception:
            return None
    if ft in ('UUIDField',):
        if isinstance(raw, uuid.UUID):
            return raw
        try:
            return uuid.UUID(str(raw))
        except Exception:
            return uuid.uuid4()
    if ft in ('BooleanField', 'NullBooleanField'):
        return bool(raw)
    if ft in ('IntegerField',):
        try:
            return int(raw)
        except Exception:
            return 0
    if ft in ('FloatField',):
        try:
            return float(raw)
        except Exception:
            return 0.0
    return str(raw) if raw is not None else ''


def _get_firestore_data():
    """Fetch all documents from all known Firestore collections."""
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        import os
        from pathlib import Path

        if not firebase_admin._apps:
            creds_json = os.environ.get('FIREBASE_CREDENTIALS_JSON')
            if creds_json:
                cred = credentials.Certificate(json.loads(creds_json))
                firebase_admin.initialize_app(cred)
            else:
                default_path = Path(__file__).resolve().parent.parent.parent.parent / 'firebase-credentials.json'
                if default_path.exists():
                    cred = credentials.Certificate(str(default_path))
                    firebase_admin.initialize_app(cred)
                else:
                    raise FileNotFoundError('No Firebase credentials found')

        db = firestore.client()
        data = {}
        for coll_name in MODEL_ORDER:
            docs = db.collection(coll_name).stream()
            rows = []
            for doc in docs:
                d = doc.to_dict()
                d['__id__'] = doc.id
                rows.append(d)
            data[coll_name] = rows
            investment_logger.info(f"  {coll_name}: {len(rows)} documents")
        return data
    except Exception as e:
        investment_logger.error(f"Failed to read Firestore: {e}")
        raise


def _import_to_mysql(data):
    """Insert all Firestore data into MySQL via Django ORM."""
    from investment import models as m

    model_name_map = {name: getattr(m, cls_name) for name, cls_name in MODEL_MAP.items()}
    total = 0
    errors = 0

    for coll_name in MODEL_ORDER:
        rows = data.get(coll_name, [])
        if not rows:
            continue
        model_class = model_name_map[coll_name]
        investment_logger.info(f"  Importing {coll_name} → {model_class.__name__}: {len(rows)} rows")

        for row in rows:
            try:
                doc_id = row.pop('__id__', None)
                kwargs = {'id': doc_id} if doc_id else {}
                for field in model_class._meta.concrete_fields:
                    name = field.attname
                    if name == 'id':
                        continue
                    raw = row.get(name)
                    kwargs[name] = _parse_value(field, raw)

                with db_transaction.atomic():
                    obj = model_class(**kwargs)
                    obj.save(force_insert=True)
                total += 1
            except Exception as e:
                errors += 1
                investment_logger.error(f"    ERROR importing {coll_name}/{row.get('__id__', '?')}: {e}")

    investment_logger.info(f"Import complete: {total} rows imported, {errors} errors")
    return total, errors


class Command(BaseCommand):
    help = 'Import all data from Firestore collections into the configured database (MySQL)'

    def handle(self, *args, **options):
        self.stdout.write('Reading data from Firestore...')
        data = _get_firestore_data()
        total_rows = sum(len(v) for v in data.values())
        self.stdout.write(f'Found {total_rows} documents across {len(data)} collections.')
        self.stdout.write('Importing into database...')
        imported, errors = _import_to_mysql(data)
        self.stdout.write(self.style.SUCCESS(f'Done. {imported} rows imported, {errors} errors.'))
