from django.contrib import admin
from . import models


class TransactionInline(admin.TabularInline):
    model = models.Transaction
    extra = 0
    fields = ['transaction_type', 'amount', 'value_date', 'status']


class LoanInline(admin.TabularInline):
    model = models.Loan
    extra = 0
    fields = ['principal_amount', 'outstanding_balance', 'interest_rate', 'tenure_months', 'status']


@admin.register(models.Investor)
class InvestorAdmin(admin.ModelAdmin):
    list_display = ['investor_code', 'name', 'category', 'kyc_status', 'email', 'phone', 'is_active']
    list_filter = ['category', 'kyc_status', 'is_active']
    search_fields = ['investor_code', 'name', 'email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [TransactionInline, LoanInline]


@admin.register(models.Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['investor_name', 'transaction_type', 'amount', 'value_date', 'payment_method', 'status']
    list_filter = ['transaction_type', 'status', 'payment_method']
    search_fields = ['investor_name', 'notes']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['investor']


class LoanScheduleInline(admin.TabularInline):
    model = models.LoanSchedule
    extra = 0
    fields = ['installment_number', 'due_date', 'scheduled_principal', 'scheduled_interest', 'paid_amount', 'payment_status']


@admin.register(models.Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ['investor_name', 'principal_amount', 'outstanding_balance', 'interest_rate', 'tenure_months', 'status']
    list_filter = ['status']
    search_fields = ['investor_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['investor']
    inlines = [LoanScheduleInline]


@admin.register(models.LoanSchedule)
class LoanScheduleAdmin(admin.ModelAdmin):
    list_display = ['loan', 'installment_number', 'due_date', 'scheduled_principal', 'scheduled_interest', 'paid_amount', 'payment_status']
    list_filter = ['payment_status']
    search_fields = ['loan__investor_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['loan']


@admin.register(models.OutboundPlacement)
class OutboundPlacementAdmin(admin.ModelAdmin):
    list_display = ['project_name', 'entity_type', 'allocated_capital', 'current_valuation', 'roi_expected_annual', 'status']
    list_filter = ['status', 'entity_type']
    search_fields = ['project_name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(models.FinancialInstrument)
class FinancialInstrumentAdmin(admin.ModelAdmin):
    list_display = ['instrument_code', 'instrument_type', 'face_value', 'coupon_rate', 'total_units_issued', 'units_outstanding']
    list_filter = ['instrument_type']
    search_fields = ['instrument_code']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(models.PLLedger)
class PLLedgerAdmin(admin.ModelAdmin):
    list_display = ['month', 'revenue', 'opex', 'interest_expense', 'net_profit']
    list_filter = ['month']
    search_fields = ['month']
    readonly_fields = ['id', 'created_at', 'updated_at']
