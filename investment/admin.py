"""
Investment Module — Django Admin

Models are registered here for admin access. Operational data
is also managed through the SPA UI and REST API.
"""

from django.contrib import admin
from investment.models import (
    Investor, Transaction, Loan, LoanSchedule,
    OutboundPlacement, FinancialInstrument, InstrumentPrice,
    PLLedger, NavHistory, InvestorHolding,
    FeeStructure, FeeAccrual, Counter,
)


@admin.register(Investor)
class InvestorAdmin(admin.ModelAdmin):
    list_display = ['name', 'investor_code', 'kyc_status', 'is_active']
    search_fields = ['name', 'investor_code']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_type', 'amount', 'status', 'created_at']
    list_filter = ['transaction_type', 'status']


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ['investor_name', 'status', 'outstanding_balance', 'created_at']
    list_filter = ['status', 'sector']


@admin.register(LoanSchedule)
class LoanScheduleAdmin(admin.ModelAdmin):
    list_display = ['installment_number', 'due_date', 'payment_status']
    list_filter = ['payment_status']


@admin.register(OutboundPlacement)
class OutboundPlacementAdmin(admin.ModelAdmin):
    list_display = ['project_name', 'allocated_capital', 'status']
    list_filter = ['status']


@admin.register(FinancialInstrument)
class FinancialInstrumentAdmin(admin.ModelAdmin):
    list_display = ['instrument_code', 'instrument_type', 'face_value', 'is_active']


@admin.register(InstrumentPrice)
class InstrumentPriceAdmin(admin.ModelAdmin):
    list_display = ['instrument', 'price_date', 'price']


@admin.register(PLLedger)
class PLLedgerAdmin(admin.ModelAdmin):
    list_display = ['month', 'revenue', 'net_profit', 'is_active']


@admin.register(NavHistory)
class NavHistoryAdmin(admin.ModelAdmin):
    list_display = ['nav_date', 'nav_per_unit', 'total_aum']


@admin.register(InvestorHolding)
class InvestorHoldingAdmin(admin.ModelAdmin):
    list_display = ['investor', 'units_held', 'current_value']


@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
    list_display = ['management_fee_annual_pct', 'performance_fee_pct']


@admin.register(FeeAccrual)
class FeeAccrualAdmin(admin.ModelAdmin):
    list_display = ['accrual_date', 'fee_type', 'amount', 'is_settled']


@admin.register(Counter)
class CounterAdmin(admin.ModelAdmin):
    list_display = ['id', 'value']
