import uuid
from django.db import models
from django.conf import settings


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    item_name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, unique=True, blank=True, null=True)
    category = models.CharField(max_length=255, default='General Sourcing')
    quantity = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    storage_location = models.CharField(max_length=255, default='Aisle A')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['item_name']
        verbose_name = 'Product'
        verbose_name_plural = 'Products'

    def __str__(self):
        return f'{self.item_name} ({self.sku or "No SKU"})'


class Vendor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    vendor_code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    contact_name = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    payment_terms = models.CharField(max_length=100, default='Net 30')
    performance_rating = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    supplied_categories = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['name']
        verbose_name = 'Vendor'
        verbose_name_plural = 'Vendors'

    def __str__(self):
        return f'{self.vendor_code} - {self.name}'


class Requisition(models.Model):
    PRIORITY_CHOICES = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
        ('Urgent', 'Urgent'),
    ]
    STATUS_CHOICES = [
        ('Pending Approval', 'Pending Approval'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Procuring', 'Procuring'),
        ('Dispatched', 'Dispatched'),
        ('Completed', 'Completed'),
        ('Partially Received', 'Partially Received'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    requisition_code = models.CharField(max_length=50, unique=True)
    client_name = models.CharField(max_length=255, blank=True, null=True)
    requested_by = models.CharField(max_length=255, blank=True, null=True)
    expected_delivery_date = models.DateField(blank=True, null=True)
    requisition_date = models.DateField(blank=True, null=True)
    priority = models.CharField(max_length=50, choices=PRIORITY_CHOICES, default='Medium')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending Approval')
    notes = models.TextField(blank=True, default='')
    items = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Requisition'
        verbose_name_plural = 'Requisitions'

    def __str__(self):
        return f'{self.requisition_code} - {self.client_name or "N/A"} ({self.status})'


class RFQ(models.Model):
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Sent', 'Sent'),
        ('Selected', 'Selected'),
        ('Cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    rfq_code = models.CharField(max_length=50, unique=True)
    requisition = models.ForeignKey(Requisition, on_delete=models.SET_NULL, blank=True, null=True, related_name='rfqs')
    deadline = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Draft')
    notes = models.TextField(blank=True, default='')
    items = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Request for Quotation'
        verbose_name_plural = 'Requests for Quotation'

    def __str__(self):
        return self.rfq_code


class Quotation(models.Model):
    STATUS_CHOICES = [
        ('Under Review', 'Under Review'),
        ('Accepted', 'Accepted'),
        ('Rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    rfq = models.ForeignKey(RFQ, on_delete=models.SET_NULL, blank=True, null=True, related_name='quotations')
    vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, blank=True, null=True, related_name='quotations')
    quotation_reference = models.CharField(max_length=255, blank=True, null=True)
    lead_time_days = models.IntegerField(default=0)
    delivery_charges = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    warranty_terms = models.TextField(blank=True, default='')
    unit_prices = models.JSONField(default=dict, blank=True)
    grand_total = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Under Review')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Quotation'
        verbose_name_plural = 'Quotations'

    def __str__(self):
        return f'{self.quotation_reference or "N/A"} - {self.vendor}'


class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Approved', 'Approved'),
        ('Cancelled', 'Cancelled'),
        ('Fulfilled', 'Fulfilled'),
        ('Partially Received', 'Partially Received'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    po_code = models.CharField(max_length=50, unique=True, verbose_name='PO Code')
    vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, blank=True, null=True, related_name='purchase_orders')
    requisition = models.ForeignKey(Requisition, on_delete=models.SET_NULL, blank=True, null=True, related_name='purchase_orders')
    quotation = models.ForeignKey(Quotation, on_delete=models.SET_NULL, blank=True, null=True, related_name='purchase_orders')
    payment_terms = models.CharField(max_length=100, default='Net 30')
    shipping_address = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Draft')
    grand_total = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    items = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Purchase Order'
        verbose_name_plural = 'Purchase Orders'

    def __str__(self):
        return f'{self.po_code} ({self.status})'


class GoodsReceipt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    grn_code = models.CharField(max_length=50, unique=True, verbose_name='GRN Code')
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.SET_NULL, blank=True, null=True, related_name='goods_receipts')
    received_by = models.CharField(max_length=255, blank=True, null=True)
    delivery_note_ref = models.CharField(max_length=255, blank=True, null=True)
    received_date = models.DateField(blank=True, null=True)
    items = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=50, default='Inspected')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Goods Receipt Note'
        verbose_name_plural = 'Goods Receipt Notes'

    def __str__(self):
        return self.grn_code


class InventoryLedger(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('PO_Receipt', 'PO Receipt'),
        ('Stock_Adjustment', 'Stock Adjustment'),
        ('Client_Handover', 'Client Handover'),
        ('Transfer', 'Transfer'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, blank=True, null=True, related_name='ledger_entries')
    product_name = models.CharField(max_length=255)
    quantity_change = models.DecimalField(max_digits=14, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    transaction_type = models.CharField(max_length=50, choices=TRANSACTION_TYPE_CHOICES)
    reference = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Inventory Ledger Entry'
        verbose_name_plural = 'Inventory Ledger Entries'

    def __str__(self):
        return f'{self.product_name} ({self.transaction_type})'


class Delivery(models.Model):
    DELIVERY_STATUS_CHOICES = [
        ('Dispatched', 'Dispatched'),
        ('Delivered', 'Delivered'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    challan_code = models.CharField(max_length=50, unique=True)
    requisition = models.ForeignKey(Requisition, on_delete=models.SET_NULL, blank=True, null=True, related_name='deliveries')
    client_name = models.CharField(max_length=255, blank=True, null=True)
    dispatched_by = models.CharField(max_length=255, blank=True, null=True)
    handover_person_name = models.CharField(max_length=255, blank=True, null=True)
    handover_contact = models.CharField(max_length=50, blank=True, null=True)
    dispatch_date = models.DateField(blank=True, null=True)
    delivery_status = models.CharField(max_length=50, choices=DELIVERY_STATUS_CHOICES, default='Dispatched')
    proof_of_delivery = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Delivery / Challan'
        verbose_name_plural = 'Deliveries / Challans'

    def __str__(self):
        return f'{self.challan_code} - {self.client_name or "N/A"}'
