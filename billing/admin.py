from django.contrib import admin
from . import models


class JournalEntryLineInline(admin.TabularInline):
    model = models.JournalEntryLine
    extra = 1
    raw_id_fields = ['account']


class InvoiceLineInline(admin.TabularInline):
    model = models.InvoiceLine
    extra = 1


class VendorBillLineInline(admin.TabularInline):
    model = models.VendorBillLine
    extra = 1


@admin.register(models.ChartOfAccount)
class ChartOfAccountAdmin(admin.ModelAdmin):
    list_display = ['account_code', 'name', 'account_type', 'currency', 'is_active']
    list_filter = ['account_type', 'is_active']
    search_fields = ['account_code', 'name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(models.JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ['entry_code', 'posting_date', 'reference_document', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['entry_code', 'reference_document', 'narration']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [JournalEntryLineInline]


@admin.register(models.Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'client_name', 'grand_total', 'status', 'issue_date', 'due_date']
    list_filter = ['status']
    search_fields = ['invoice_number', 'client_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [InvoiceLineInline]


@admin.register(models.VendorBill)
class VendorBillAdmin(admin.ModelAdmin):
    list_display = ['bill_number', 'vendor_name', 'grand_total', 'status', 'issue_date', 'due_date']
    list_filter = ['status']
    search_fields = ['bill_number', 'vendor_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [VendorBillLineInline]


@admin.register(models.Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['receipt_code', 'payment_date', 'amount', 'payment_method', 'invoice']
    list_filter = ['payment_method']
    search_fields = ['receipt_code', 'bank_reference']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['invoice', 'vendor_bill']


@admin.register(models.TaxCode)
class TaxCodeAdmin(admin.ModelAdmin):
    list_display = ['tax_code', 'name', 'rate_percentage', 'is_active']
    list_filter = ['is_active']
    search_fields = ['tax_code', 'name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(models.AuditTrail)
class AuditTrailAdmin(admin.ModelAdmin):
    list_display = ['action_type', 'performed_by_name', 'created_at']
    list_filter = ['action_type']
    search_fields = ['action_type', 'performed_by_name']
    readonly_fields = ['id', 'created_at']


@admin.register(models.JournalEntryLine)
class JournalEntryLineAdmin(admin.ModelAdmin):
    list_display = ['journal_entry', 'account', 'debit_amount', 'credit_amount']
    list_filter = ['account']
    raw_id_fields = ['journal_entry', 'account']
    readonly_fields = ['id', 'created_at']


@admin.register(models.InvoiceLine)
class InvoiceLineAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'description', 'quantity', 'unit_price', 'line_total']
    search_fields = ['description']
    raw_id_fields = ['invoice']
    readonly_fields = ['id', 'created_at']


@admin.register(models.VendorBillLine)
class VendorBillLineAdmin(admin.ModelAdmin):
    list_display = ['vendor_bill', 'description', 'quantity', 'unit_price', 'line_total']
    search_fields = ['description']
    raw_id_fields = ['vendor_bill']
    readonly_fields = ['id', 'created_at']
