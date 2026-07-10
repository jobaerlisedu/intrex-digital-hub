from rest_framework import serializers
from investment.services import money_to_str, money_to_float
from investment.models import (
    INVESTOR_CATEGORIES, KYC_STATUSES,
    TRANSACTION_TYPES, PAYMENT_METHODS, TRANSACTION_STATUSES,
    LOAN_STATUSES, LOAN_SCHEDULE_PAYMENT_STATUSES,
    OUTBOUND_ENTITY_TYPES, OUTBOUND_STATUSES,
    INSTRUMENT_TYPES,
)


class MoneyField(serializers.FloatField):
    """FloatField that serializes to BDT formatted string and accepts string input."""

    def to_representation(self, value):
        return money_to_str(value)

    def to_internal_value(self, data):
        if isinstance(data, str):
            return money_to_float(data)
        return super().to_internal_value(data)


class InvestorSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    investor_code = serializers.CharField(max_length=50)
    name = serializers.CharField(max_length=255)
    category = serializers.ChoiceField(choices=INVESTOR_CATEGORIES, default='Individual')
    kyc_status = serializers.ChoiceField(choices=KYC_STATUSES, default='Pending')
    tax_id = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    email = serializers.EmailField(max_length=255, required=False, allow_blank=True, default='')
    phone = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    bank_account_name = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    bank_account_number = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    bank_routing_code = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    contact_id = serializers.CharField(required=False, allow_blank=True, default='')
    is_active = serializers.BooleanField(default=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    created_by = serializers.CharField(read_only=True)
    updated_by = serializers.CharField(read_only=True)

    transactions = serializers.ListField(child=serializers.DictField(), read_only=True, default=[])
    loans = serializers.ListField(child=serializers.DictField(), read_only=True, default=[])


class TransactionSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    investor_id = serializers.CharField(max_length=255)
    investor_name = serializers.CharField(max_length=255)
    transaction_type = serializers.ChoiceField(choices=TRANSACTION_TYPES)
    amount = MoneyField()
    payment_method = serializers.ChoiceField(choices=PAYMENT_METHODS, default='Bank Wire')
    value_date = serializers.CharField(max_length=10)
    status = serializers.ChoiceField(choices=TRANSACTION_STATUSES, default='Cleared')
    notes = serializers.CharField(required=False, allow_blank=True, default='')
    is_active = serializers.BooleanField(default=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    created_by = serializers.CharField(read_only=True)
    updated_by = serializers.CharField(read_only=True)


class LoanSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    investor_id = serializers.CharField(max_length=255)
    investor_name = serializers.CharField(max_length=255)
    principal_amount = MoneyField()
    outstanding_balance = MoneyField()
    interest_rate = serializers.FloatField()
    tenure_months = serializers.IntegerField()
    disbursement_date = serializers.CharField(max_length=10)
    status = serializers.ChoiceField(choices=LOAN_STATUSES, default='Active')
    is_active = serializers.BooleanField(default=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    created_by = serializers.CharField(read_only=True)
    updated_by = serializers.CharField(read_only=True)


class LoanScheduleSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    loan_id = serializers.CharField(max_length=255)
    installment_number = serializers.IntegerField()
    due_date = serializers.CharField(max_length=10)
    scheduled_principal = MoneyField()
    scheduled_interest = MoneyField()
    paid_amount = MoneyField(default=0.0)
    payment_status = serializers.ChoiceField(choices=LOAN_SCHEDULE_PAYMENT_STATUSES, default='Unpaid')
    actual_payment_date = serializers.CharField(max_length=10, required=False, allow_null=True, default=None)
    is_active = serializers.BooleanField(default=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class OutboundPlacementSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    project_name = serializers.CharField(max_length=255)
    entity_type = serializers.ChoiceField(choices=OUTBOUND_ENTITY_TYPES, default='Subsidiary')
    allocated_capital = MoneyField(default=0.0)
    current_valuation = MoneyField(default=0.0)
    roi_expected_annual = serializers.FloatField(default=0.0)
    placement_date = serializers.CharField(max_length=10)
    status = serializers.ChoiceField(choices=OUTBOUND_STATUSES, default='Active')
    is_active = serializers.BooleanField(default=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    created_by = serializers.CharField(read_only=True)
    updated_by = serializers.CharField(read_only=True)


class FinancialInstrumentSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    instrument_code = serializers.CharField(max_length=100)
    type = serializers.ChoiceField(choices=INSTRUMENT_TYPES, default='Common Stock')
    face_value = MoneyField(default=0.0)
    coupon_rate = serializers.FloatField(default=0.0)
    total_units_issued = serializers.IntegerField(default=0)
    units_outstanding = serializers.IntegerField(default=0)
    issue_date = serializers.CharField(max_length=10)
    is_active = serializers.BooleanField(default=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    created_by = serializers.CharField(read_only=True)
    updated_by = serializers.CharField(read_only=True)


class PLLedgerSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    month = serializers.CharField(max_length=7)
    revenue = MoneyField(default=0.0)
    opex = MoneyField(default=0.0)
    interest_expense = MoneyField(default=0.0)
    net_profit = MoneyField(default=0.0)
    is_active = serializers.BooleanField(default=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    created_by = serializers.CharField(read_only=True)
    updated_by = serializers.CharField(read_only=True)


class InstrumentPriceSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    instrument_id = serializers.CharField(max_length=255)
    price_date = serializers.CharField(max_length=10)
    price = MoneyField()
    is_active = serializers.BooleanField(default=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    created_by = serializers.CharField(read_only=True)
    updated_by = serializers.CharField(read_only=True)


class NavHistorySerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    nav_date = serializers.CharField(max_length=10)
    nav_per_unit = serializers.CharField(max_length=20)
    total_units = serializers.CharField(max_length=20)
    total_aum = serializers.CharField(max_length=20)
    management_fee_accrued = serializers.CharField(default='0.00')
    performance_fee_accrued = serializers.CharField(default='0.00')
    total_liabilities = serializers.CharField(default='0.00')
    is_active = serializers.BooleanField(default=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    created_by = serializers.CharField(read_only=True)
    updated_by = serializers.CharField(read_only=True)


class InvestorHoldingSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    investor_id = serializers.CharField(max_length=255)
    units_held = serializers.CharField(default='0.0000')
    avg_cost_per_unit = serializers.CharField(default='0.0000')
    total_invested = serializers.CharField(default='0.00')
    current_value = serializers.CharField(default='0.00')
    unrealized_pl = serializers.CharField(default='0.00')
    is_active = serializers.BooleanField(default=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    created_by = serializers.CharField(read_only=True)
    updated_by = serializers.CharField(read_only=True)


class FeeStructureSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    management_fee_annual_pct = serializers.CharField(default='2.00')
    performance_fee_pct = serializers.CharField(default='20.00')
    hurdle_rate_pct = serializers.CharField(default='5.00')
    high_water_mark = serializers.CharField(default='0.0000')
    fee_frequency = serializers.ChoiceField(choices=['monthly', 'quarterly', 'annual'], default='monthly')
    is_active = serializers.BooleanField(default=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    created_by = serializers.CharField(read_only=True)
    updated_by = serializers.CharField(read_only=True)


class FeeAccrualSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    accrual_date = serializers.CharField(max_length=10)
    fee_type = serializers.ChoiceField(choices=['management', 'performance'])
    amount = serializers.CharField()
    nav_before_fee = serializers.CharField(default='0.00')
    nav_after_fee = serializers.CharField(default='0.00')
    is_settled = serializers.BooleanField(default=False)
    settled_date = serializers.CharField(required=False, allow_null=True, default=None)
    is_active = serializers.BooleanField(default=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    created_by = serializers.CharField(read_only=True)
    updated_by = serializers.CharField(read_only=True)


# ── Portal Serializers ───────────────────────────────────────

class PortalHoldingSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    investor_id = serializers.CharField()
    units_held = serializers.CharField()
    avg_cost_per_unit = serializers.CharField()
    total_invested = serializers.CharField()
    current_value = serializers.CharField()
    unrealized_pl = serializers.CharField()


class PortalTransactionSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    transaction_type = serializers.CharField()
    amount = serializers.CharField()
    payment_method = serializers.CharField()
    value_date = serializers.CharField()
    status = serializers.CharField()
    notes = serializers.CharField()


class PortalDashboardSerializer(serializers.Serializer):
    investor = serializers.DictField()
    holdings = PortalHoldingSerializer(many=True)
    recent_transactions = PortalTransactionSerializer(many=True)
    total_invested = serializers.FloatField()
    total_value = serializers.FloatField()
    total_pl = serializers.FloatField()
    return_pct = serializers.FloatField()
    current_nav = serializers.DictField(allow_null=True)
