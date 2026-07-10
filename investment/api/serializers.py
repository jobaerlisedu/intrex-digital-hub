from rest_framework import serializers
from investment.models import (
    INVESTOR_CATEGORIES, KYC_STATUSES,
    TRANSACTION_TYPES, PAYMENT_METHODS, TRANSACTION_STATUSES,
    LOAN_STATUSES, LOAN_SCHEDULE_PAYMENT_STATUSES,
    OUTBOUND_ENTITY_TYPES, OUTBOUND_STATUSES,
    INSTRUMENT_TYPES,
)


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
    amount = serializers.FloatField()
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
    principal_amount = serializers.FloatField()
    outstanding_balance = serializers.FloatField()
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
    scheduled_principal = serializers.FloatField()
    scheduled_interest = serializers.FloatField()
    paid_amount = serializers.FloatField(default=0.0)
    payment_status = serializers.ChoiceField(choices=LOAN_SCHEDULE_PAYMENT_STATUSES, default='Unpaid')
    actual_payment_date = serializers.CharField(max_length=10, required=False, allow_null=True, default=None)
    is_active = serializers.BooleanField(default=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class OutboundPlacementSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    project_name = serializers.CharField(max_length=255)
    entity_type = serializers.ChoiceField(choices=OUTBOUND_ENTITY_TYPES, default='Subsidiary')
    allocated_capital = serializers.FloatField(default=0.0)
    current_valuation = serializers.FloatField(default=0.0)
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
    face_value = serializers.FloatField(default=0.0)
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
    revenue = serializers.FloatField(default=0.0)
    opex = serializers.FloatField(default=0.0)
    interest_expense = serializers.FloatField(default=0.0)
    net_profit = serializers.FloatField(default=0.0)
    is_active = serializers.BooleanField(default=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    created_by = serializers.CharField(read_only=True)
    updated_by = serializers.CharField(read_only=True)
