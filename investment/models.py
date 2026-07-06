import uuid
from django.db import models
from django.conf import settings


class Investor(models.Model):
    CATEGORY_CHOICES = [
        ('Individual', 'Individual'),
        ('Corporate', 'Corporate'),
        ('Institutional', 'Institutional'),
    ]
    KYC_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Verified', 'Verified'),
        ('Rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    investor_code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Individual')
    kyc_status = models.CharField(max_length=50, choices=KYC_STATUS_CHOICES, default='Pending')
    tax_id = models.CharField(max_length=100, blank=True, default='')
    email = models.EmailField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    bank_account_name = models.CharField(max_length=255, blank=True, default='')
    bank_account_number = models.CharField(max_length=100, blank=True, default='')
    bank_routing_code = models.CharField(max_length=100, blank=True, default='')
    contact_id = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['name']
        verbose_name = 'Investor'
        verbose_name_plural = 'Investors'

    def __str__(self):
        return f'{self.investor_code} - {self.name}'


class Transaction(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('Capital Influx', 'Capital Influx'),
        ('Capital Withdrawal', 'Capital Withdrawal'),
        ('Interest Payout', 'Interest Payout'),
        ('Dividend Payout', 'Dividend Payout'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('Bank Wire', 'Bank Wire'),
        ('Cheque', 'Cheque'),
        ('Cash', 'Cash'),
        ('Mobile Banking', 'Mobile Banking'),
    ]
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Cleared', 'Cleared'),
        ('Failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    investor = models.ForeignKey(Investor, on_delete=models.CASCADE, related_name='transactions')
    investor_name = models.CharField(max_length=255)
    transaction_type = models.CharField(max_length=50, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES, default='Bank Wire')
    value_date = models.DateField()
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Cleared')
    notes = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'

    def __str__(self):
        return f'{self.investor_name} - {self.transaction_type} ({self.amount})'


class Loan(models.Model):
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Fully Paid', 'Fully Paid'),
        ('Defaulted', 'Defaulted'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    investor = models.ForeignKey(Investor, on_delete=models.CASCADE, related_name='loans')
    investor_name = models.CharField(max_length=255)
    principal_amount = models.DecimalField(max_digits=16, decimal_places=2)
    outstanding_balance = models.DecimalField(max_digits=16, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=6, decimal_places=2, verbose_name='Interest Rate (%)')
    tenure_months = models.IntegerField()
    disbursement_date = models.DateField()
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Active')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Loan'
        verbose_name_plural = 'Loans'

    def __str__(self):
        return f'{self.investor_name} - {self.principal_amount} ({self.status})'


class LoanSchedule(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('Unpaid', 'Unpaid'),
        ('Paid', 'Paid'),
        ('Overdue', 'Overdue'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='schedules')
    installment_number = models.IntegerField()
    due_date = models.DateField()
    scheduled_principal = models.DecimalField(max_digits=16, decimal_places=2)
    scheduled_interest = models.DecimalField(max_digits=16, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=50, choices=PAYMENT_STATUS_CHOICES, default='Unpaid')
    actual_payment_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['loan', 'installment_number']
        verbose_name = 'Loan Schedule'
        verbose_name_plural = 'Loan Schedules'

    def __str__(self):
        return f'{self.loan.investor_name} - Installment {self.installment_number}'


class OutboundPlacement(models.Model):
    ENTITY_TYPE_CHOICES = [
        ('Subsidiary', 'Subsidiary'),
        ('Joint Venture', 'Joint Venture'),
        ('Investment Fund', 'Investment Fund'),
        ('Other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Divested', 'Divested'),
        ('Suspended', 'Suspended'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    project_name = models.CharField(max_length=255)
    entity_type = models.CharField(max_length=50, choices=ENTITY_TYPE_CHOICES, default='Subsidiary')
    allocated_capital = models.DecimalField(max_digits=16, decimal_places=2)
    current_valuation = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    roi_expected_annual = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name='Expected Annual ROI (%)')
    placement_date = models.DateField()
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Active')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Outbound Placement'
        verbose_name_plural = 'Outbound Placements'

    def __str__(self):
        return f'{self.project_name} ({self.status})'


class FinancialInstrument(models.Model):
    INSTRUMENT_TYPE_CHOICES = [
        ('Common Stock', 'Common Stock'),
        ('Preferred Stock', 'Preferred Stock'),
        ('Corporate Bond', 'Corporate Bond'),
        ('Government Bond', 'Government Bond'),
        ('Mutual Fund', 'Mutual Fund'),
        ('Other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    instrument_code = models.CharField(max_length=100, unique=True)
    instrument_type = models.CharField(max_length=50, choices=INSTRUMENT_TYPE_CHOICES, default='Common Stock', verbose_name='Type')
    face_value = models.DecimalField(max_digits=16, decimal_places=2)
    coupon_rate = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name='Coupon Rate (%)')
    total_units_issued = models.IntegerField()
    units_outstanding = models.IntegerField()
    issue_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['instrument_code']
        verbose_name = 'Financial Instrument'
        verbose_name_plural = 'Financial Instruments'

    def __str__(self):
        return f'{self.instrument_code} ({self.instrument_type})'


class PLLedger(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    month = models.CharField(max_length=7, verbose_name='Month (YYYY-MM)')
    revenue = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    opex = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    interest_expense = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    net_profit = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-month']
        verbose_name = 'P&L Ledger Entry'
        verbose_name_plural = 'P&L Ledger Entries'
        unique_together = ['month']

    def __str__(self):
        return f'{self.month} - Net: {self.net_profit}'
