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
    amount: str
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
    principal_amount: str
    outstanding_balance: str
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
    scheduled_principal: str
    scheduled_interest: str
    paid_amount: str = "0.00"
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
    allocated_capital: str = "0.00"
    current_valuation: str = "0.00"
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
    face_value: str = "0.00"
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
    price: str
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: str = ''
    updated_by: str = ''


@dataclass
class PLLedgerSchema:
    """Collection: invst_pl_ledger"""
    month: str  # YYYY-MM
    revenue: str = "0.00"
    opex: str = "0.00"
    interest_expense: str = "0.00"
    net_profit: str = "0.00"
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: str = ''
    updated_by: str = ''


@dataclass
class NavSchema:
    """Collection: invst_nav_history"""
    nav_date: str
    nav_per_unit: str
    total_units: str
    total_aum: str
    management_fee_accrued: str = "0.00"
    performance_fee_accrued: str = "0.00"
    total_liabilities: str = "0.00"
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: str = ""
    updated_by: str = ""


@dataclass
class InvestorHoldingSchema:
    """Collection: invst_investor_holdings"""
    investor_id: str
    units_held: str = "0.0000"
    avg_cost_per_unit: str = "0.0000"
    total_invested: str = "0.00"
    current_value: str = "0.00"
    unrealized_pl: str = "0.00"
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: str = ""
    updated_by: str = ""


@dataclass
class FeeStructureSchema:
    """Collection: invst_fee_structures"""
    management_fee_annual_pct: str = "2.00"
    performance_fee_pct: str = "20.00"
    hurdle_rate_pct: str = "5.00"
    high_water_mark: str = "0.0000"
    fee_frequency: str = "monthly"
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: str = ""
    updated_by: str = ""


@dataclass
class FeeAccrualSchema:
    """Collection: invst_fee_accruals"""
    accrual_date: str
    fee_type: str
    amount: str
    nav_before_fee: str = "0.00"
    nav_after_fee: str = "0.00"
    is_settled: bool = False
    settled_date: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: str = ""
    updated_by: str = ""


# ══════════════════════════════════════════════
# CURRENCY SUPPORT SCHEMAS (Phase 7)
# ══════════════════════════════════════════════

@dataclass
class CurrencyConfigSchema:
    """Collection: invst_currency_config"""
    base_currency: str = "BDT"
    fx_rate_source: str = "manual"
    last_updated: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class FxRateSchema:
    """Collection: invst_fx_rates"""
    from_currency: str
    to_currency: str
    rate: str
    rate_date: str
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
