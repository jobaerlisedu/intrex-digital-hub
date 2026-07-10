"""
Firestore Document Schemas — Investment Module

This module defines the authoritative schema contracts for all Firestore
collections used by the Investment module. These are NOT Django ORM models;
no database tables are created. Firestore is the sole data store.

Collection naming convention: invst_<entity>
"""

from dataclasses import dataclass, field, asdict
from typing import Optional
from decimal import Decimal
from datetime import date, datetime


# ──────────────────────────────────────────────
# Shared Constants (aligned with templates)
# ──────────────────────────────────────────────

INVESTOR_CATEGORIES = [
    'Individual', 'Corporate', 'Institutional',
    'Venture Capital', 'Angel',
]

KYC_STATUSES = [
    'Pending', 'Verified', 'Expired', 'Rejected',
]

TRANSACTION_TYPES = [
    'Capital Influx', 'Capital Withdrawal',
    'Interest Payout', 'Dividend Payout',
]

PAYMENT_METHODS = [
    'Bank Wire', 'Cheque', 'Cash', 'Mobile Banking',
]

TRANSACTION_STATUSES = [
    'Pending', 'Cleared', 'Failed',
]

LOAN_STATUSES = [
    'Active', 'Fully Paid', 'Defaulted',
]

LOAN_SCHEDULE_PAYMENT_STATUSES = [
    'Unpaid', 'Paid', 'Overdue',
]

OUTBOUND_ENTITY_TYPES = [
    'Subsidiary', 'Joint Venture', 'Investment Fund', 'Other',
]

OUTBOUND_STATUSES = [
    'Active', 'Divested', 'Suspended',
]

INSTRUMENT_TYPES = [
    'Common Stock', 'Preferred Stock', 'Corporate Bond',
    'Government Bond', 'Mutual Fund', 'Other',
]


# ──────────────────────────────────────────────
# Firestore Document Schemas
# ──────────────────────────────────────────────
# Each dataclass maps 1:1 to fields stored in the corresponding
# invst_* Firestore document. Fields named 'id' are omitted because
# Firestore document IDs are stored separately.

@dataclass
class InvestorSchema:
    """Collection: invst_investors"""
    investor_code: str
    name: str
    category: str = 'Individual'
    kyc_status: str = 'Pending'
    tax_id: str = ''
    email: str = ''
    phone: str = ''
    bank_account_name: str = ''
    bank_account_number: str = ''
    bank_routing_code: str = ''
    contact_id: str = ''
    kyc_document_url: str = ''
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: str = ''
    updated_by: str = ''


@dataclass
class TransactionSchema:
    """Collection: invst_transactions"""
    investor_id: str
    investor_name: str
    transaction_type: str
    amount: float
    payment_method: str = 'Bank Wire'
    value_date: str = ''
    status: str = 'Cleared'
    notes: str = ''
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: str = ''
    updated_by: str = ''


@dataclass
class LoanSchema:
    """Collection: invst_loans"""
    investor_id: str
    investor_name: str
    principal_amount: float
    outstanding_balance: float
    interest_rate: float
    tenure_months: int
    disbursement_date: str
    status: str = 'Active'
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: str = ''
    updated_by: str = ''


@dataclass
class LoanScheduleSchema:
    """Collection: invst_loan_schedules"""
    loan_id: str
    installment_number: int
    due_date: str
    scheduled_principal: float
    scheduled_interest: float
    paid_amount: float = 0.0
    payment_status: str = 'Unpaid'
    actual_payment_date: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class OutboundPlacementSchema:
    """Collection: invst_outbound_placements"""
    project_name: str
    entity_type: str = 'Subsidiary'
    allocated_capital: float = 0.0
    current_valuation: float = 0.0
    roi_expected_annual: float = 0.0
    placement_date: str = ''
    status: str = 'Active'
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: str = ''
    updated_by: str = ''


@dataclass
class FinancialInstrumentSchema:
    """Collection: invst_financial_instruments"""
    instrument_code: str
    instrument_type: str = 'Common Stock'
    face_value: float = 0.0
    coupon_rate: float = 0.0
    total_units_issued: int = 0
    units_outstanding: int = 0
    issue_date: str = ''
    maturity_date: str = ''
    sector: str = ''
    isin: str = ''
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: str = ''
    updated_by: str = ''


@dataclass
class InstrumentPriceSchema:
    """Collection: invst_instrument_prices"""
    instrument_id: str
    price_date: str
    price: float
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: str = ''
    updated_by: str = ''


@dataclass
class PLLedgerSchema:
    """Collection: invst_pl_ledger"""
    month: str  # YYYY-MM
    revenue: float = 0.0
    opex: float = 0.0
    interest_expense: float = 0.0
    net_profit: float = 0.0
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: str = ''
    updated_by: str = ''
