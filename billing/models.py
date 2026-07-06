import uuid
from django.db import models
from django.conf import settings


class ChartOfAccount(models.Model):
    ACCOUNT_TYPE_CHOICES = [
        ('Asset', 'Asset'),
        ('Liability', 'Liability'),
        ('Equity', 'Equity'),
        ('Revenue', 'Revenue'),
        ('Expense', 'Expense'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    account_code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    account_type = models.CharField(max_length=50, choices=ACCOUNT_TYPE_CHOICES)
    currency = models.CharField(max_length=10, default='BDT')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['account_code']
        verbose_name = 'Chart of Account'
        verbose_name_plural = 'Chart of Accounts'

    def __str__(self):
        return f'{self.account_code} - {self.name}'


class JournalEntry(models.Model):
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Posted', 'Posted'),
        ('Voided', 'Voided'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    entry_code = models.CharField(max_length=50, unique=True)
    posting_date = models.DateField()
    reference_document = models.CharField(max_length=255, blank=True, null=True)
    narration = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Draft')
    created_by_name = models.CharField(max_length=255, blank=True, null=True, verbose_name='Created by (name)')
    approved_by_name = models.CharField(max_length=255, blank=True, null=True, verbose_name='Approved by (name)')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Journal Entry'
        verbose_name_plural = 'Journal Entries'

    def __str__(self):
        return f'{self.entry_code} ({self.status})'


class JournalEntryLine(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='lines')
    account = models.ForeignKey(ChartOfAccount, on_delete=models.CASCADE, related_name='journal_lines')
    debit_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    credit_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['account']
        verbose_name = 'Journal Entry Line'
        verbose_name_plural = 'Journal Entry Lines'

    def __str__(self):
        return f'{self.journal_entry.entry_code} - {self.account.name}'


class Invoice(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Paid', 'Paid'),
        ('Partially Paid', 'Partially Paid'),
        ('Overdue', 'Overdue'),
        ('Cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    invoice_number = models.CharField(max_length=100, unique=True)
    client_name = models.CharField(max_length=255)
    issue_date = models.DateField()
    due_date = models.DateField()
    subtotal = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'

    def __str__(self):
        return f'{self.invoice_number} - {self.client_name} ({self.status})'


class InvoiceLine(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='lines')
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=14, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)
    line_total = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['description']
        verbose_name = 'Invoice Line'
        verbose_name_plural = 'Invoice Lines'

    def __str__(self):
        return f'{self.invoice.invoice_number} - {self.description}'


class VendorBill(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Paid', 'Paid'),
        ('Partially Paid', 'Partially Paid'),
        ('Cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    bill_number = models.CharField(max_length=100, unique=True)
    vendor_name = models.CharField(max_length=255)
    issue_date = models.DateField()
    due_date = models.DateField()
    grand_total = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Vendor Bill'
        verbose_name_plural = 'Vendor Bills'

    def __str__(self):
        return f'{self.bill_number} - {self.vendor_name} ({self.status})'


class VendorBillLine(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor_bill = models.ForeignKey(VendorBill, on_delete=models.CASCADE, related_name='lines')
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=14, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)
    line_total = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Vendor Bill Line'
        verbose_name_plural = 'Vendor Bill Lines'

    def __str__(self):
        return f'{self.vendor_bill.bill_number} - {self.description}'


class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('Cash', 'Cash'),
        ('Bank Transfer', 'Bank Transfer'),
        ('Cheque', 'Cheque'),
        ('Mobile Banking', 'Mobile Banking'),
        ('Card', 'Card'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    receipt_code = models.CharField(max_length=100, unique=True)
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, blank=True, null=True, related_name='payments')
    vendor_bill = models.ForeignKey(VendorBill, on_delete=models.SET_NULL, blank=True, null=True, related_name='payments')
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES, default='Cash')
    bank_reference = models.CharField(max_length=255, blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'

    def __str__(self):
        return f'{self.receipt_code} - {self.amount}'


class TaxCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    tax_code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    rate_percentage = models.DecimalField(max_digits=6, decimal_places=2)
    tax_authority = models.CharField(max_length=255, default='National Revenue Authority')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['tax_code']
        verbose_name = 'Tax Code'
        verbose_name_plural = 'Tax Codes'

    def __str__(self):
        return f'{self.tax_code} ({self.rate_percentage}%)'


class AuditTrail(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    action_type = models.CharField(max_length=100)
    performed_by_name = models.CharField(max_length=255, blank=True, null=True)
    payload_before = models.JSONField(default=dict, blank=True)
    payload_after = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Audit Trail Entry'
        verbose_name_plural = 'Audit Trail Entries'

    def __str__(self):
        return f'{self.action_type} @ {self.created_at}'
