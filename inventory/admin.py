from django.contrib import admin
from . import models


@admin.register(models.Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['item_name', 'sku', 'category', 'quantity', 'unit_price', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['item_name', 'sku']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(models.Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ['vendor_code', 'name', 'email', 'phone', 'performance_rating', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'vendor_code', 'email']
    readonly_fields = ['id', 'created_at', 'updated_at']


class RFQInline(admin.TabularInline):
    model = models.RFQ
    extra = 0
    fields = ['rfq_code', 'status', 'deadline']


@admin.register(models.Requisition)
class RequisitionAdmin(admin.ModelAdmin):
    list_display = ['requisition_code', 'client_name', 'priority', 'status', 'created_at']
    list_filter = ['status', 'priority']
    search_fields = ['requisition_code', 'client_name', 'notes']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [RFQInline]


@admin.register(models.RFQ)
class RFQAdmin(admin.ModelAdmin):
    list_display = ['rfq_code', 'requisition', 'deadline', 'status']
    list_filter = ['status']
    search_fields = ['rfq_code']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['requisition']


@admin.register(models.Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ['quotation_reference', 'vendor', 'rfq', 'grand_total', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['quotation_reference', 'vendor__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['rfq', 'vendor']


class GoodsReceiptInline(admin.TabularInline):
    model = models.GoodsReceipt
    extra = 0
    fields = ['grn_code', 'received_date', 'status']


@admin.register(models.PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['po_code', 'vendor', 'grand_total', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['po_code', 'vendor__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['vendor', 'requisition', 'quotation']
    inlines = [GoodsReceiptInline]


@admin.register(models.GoodsReceipt)
class GoodsReceiptAdmin(admin.ModelAdmin):
    list_display = ['grn_code', 'purchase_order', 'received_date', 'received_by', 'status']
    list_filter = ['status']
    search_fields = ['grn_code', 'purchase_order__po_code']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['purchase_order']


@admin.register(models.InventoryLedger)
class InventoryLedgerAdmin(admin.ModelAdmin):
    list_display = ['product_name', 'quantity_change', 'unit_cost', 'transaction_type', 'created_at']
    list_filter = ['transaction_type']
    search_fields = ['product_name']
    readonly_fields = ['id', 'created_at']
    raw_id_fields = ['product']


@admin.register(models.Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ['challan_code', 'client_name', 'dispatch_date', 'delivery_status']
    list_filter = ['delivery_status']
    search_fields = ['challan_code', 'client_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['requisition']
