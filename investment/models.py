import uuid
from django.db import models
from django.conf import settings


class Investor(models.Model):
    CATEGORY_CHOICES = [
        ('Individual', 'Individual'), ('Corporate', 'Corporate'),
        ('Institutional', 'Institutional'), ('Venture Capital', 'Venture Capital'),
        ('Angel', 'Angel'),
    ]
    KYC_CHOICES = [
        ('Pending', 'Pending'), ('Verified', 'Verified'),
        ('Expired', 'Expired'), ('Rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    investor_code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Individual')
    kyc_status = models.CharField(max_length=50, choices=KYC_CHOICES, default='Pending')
    tax_id = models.CharField(max_length=100, blank=True, default='')
    email = models.EmailField(max_length=255, blank=True, default='')
    phone = models.CharField(max_length=50, blank=True, default='')
    bank_account_name = models.CharField(max_length=255, blank=True, default='')
    bank_account_number = models.CharField(max_length=100, blank=True, default='')
    bank_routing_code = models.CharField(max_length=100, blank=True, default='')
    contact_id = models.CharField(max_length=255, blank=True, default='')
    kyc_document = models.FileField(upload_to='kyc/', blank=True)
    password_hash = models.CharField(max_length=255, blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=255, blank=True, default='')
    updated_by = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['name']
        verbose_name = 'Investor'
        verbose_name_plural = 'Investors'

    @property
    def kyc_document_url(self):
        return self.kyc_document.url if self.kyc_document else ''

    def __str__(self):
        return f'{self.investor_code} - {self.name}'


class Transaction(models.Model):
    TX_TYPES = [
        ('Capital Influx', 'Capital Influx'), ('Capital Withdrawal', 'Capital Withdrawal'),
        ('Interest Payout', 'Interest Payout'), ('Dividend Payout', 'Dividend Payout'),
    ]
    PAYMENT_METHODS = [
        ('Bank Wire', 'Bank Wire'), ('Cheque', 'Cheque'),
        ('Cash', 'Cash'), ('Mobile Banking', 'Mobile Banking'),
    ]
    TX_STATUSES = [('Pending', 'Pending'), ('Cleared', 'Cleared'), ('Failed', 'Failed')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    investor = models.ForeignKey(Investor, on_delete=models.CASCADE, related_name='transactions')
    investor_name = models.CharField(max_length=255, blank=True, default='')
    transaction_type = models.CharField(max_length=50, choices=TX_TYPES)
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHODS, default='Bank Wire')
    value_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=TX_STATUSES, default='Cleared')
    notes = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=255, blank=True, default='')
    updated_by = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'

    def __str__(self):
        return f'{self.investor_name} - {self.transaction_type} - {self.amount}'


class Loan(models.Model):
    LOAN_STATUSES = [('Active', 'Active'), ('Fully Paid', 'Fully Paid'), ('Defaulted', 'Defaulted')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    investor = models.ForeignKey(Investor, on_delete=models.CASCADE, related_name='loans')
    investor_name = models.CharField(max_length=255, blank=True, default='')
    principal_amount = models.DecimalField(max_digits=16, decimal_places=2)
    outstanding_balance = models.DecimalField(max_digits=16, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=6, decimal_places=2, help_text='Annual rate in percent')
    tenure_months = models.IntegerField()
    disbursement_date = models.DateField()
    status = models.CharField(max_length=50, choices=LOAN_STATUSES, default='Active')
    sector = models.CharField(max_length=255, blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=255, blank=True, default='')
    updated_by = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Loan'
        verbose_name_plural = 'Loans'

    def __str__(self):
        return f'{self.investor_name} - {self.principal_amount}'


class LoanSchedule(models.Model):
    PAYMENT_STATUSES = [('Unpaid', 'Unpaid'), ('Paid', 'Paid'), ('Overdue', 'Overdue')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='schedules')
    installment_number = models.IntegerField()
    due_date = models.DateField()
    scheduled_principal = models.DecimalField(max_digits=16, decimal_places=2)
    scheduled_interest = models.DecimalField(max_digits=16, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=50, choices=PAYMENT_STATUSES, default='Unpaid')
    actual_payment_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['loan', 'installment_number']
        verbose_name = 'Loan Schedule'
        verbose_name_plural = 'Loan Schedules'
        unique_together = ['loan', 'installment_number']

    def __str__(self):
        return f'{self.loan} - Inst #{self.installment_number}'


class OutboundPlacement(models.Model):
    ENTITY_TYPES = [
        ('Subsidiary', 'Subsidiary'), ('Joint Venture', 'Joint Venture'),
        ('Investment Fund', 'Investment Fund'), ('Other', 'Other'),
    ]
    STATUSES = [('Active', 'Active'), ('Divested', 'Divested'), ('Suspended', 'Suspended')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project_name = models.CharField(max_length=255)
    entity_type = models.CharField(max_length=50, choices=ENTITY_TYPES, default='Subsidiary')
    allocated_capital = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    current_valuation = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    roi_expected_annual = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    placement_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUSES, default='Active')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=255, blank=True, default='')
    updated_by = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Outbound Placement'
        verbose_name_plural = 'Outbound Placements'

    def __str__(self):
        return self.project_name


class FinancialInstrument(models.Model):
    INSTRUMENT_TYPES = [
        ('Common Stock', 'Common Stock'), ('Preferred Stock', 'Preferred Stock'),
        ('Corporate Bond', 'Corporate Bond'), ('Government Bond', 'Government Bond'),
        ('Mutual Fund', 'Mutual Fund'), ('Other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    instrument_code = models.CharField(max_length=100, unique=True)
    instrument_type = models.CharField(max_length=50, choices=INSTRUMENT_TYPES, default='Common Stock')
    face_value = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    coupon_rate = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    total_units_issued = models.IntegerField(default=0)
    units_outstanding = models.IntegerField(default=0)
    issue_date = models.DateField(blank=True, null=True)
    maturity_date = models.DateField(blank=True, null=True)
    sector = models.CharField(max_length=255, blank=True, default='')
    isin = models.CharField(max_length=50, blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=255, blank=True, default='')
    updated_by = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['instrument_code']
        verbose_name = 'Financial Instrument'
        verbose_name_plural = 'Financial Instruments'

    def __str__(self):
        return f'{self.instrument_code} ({self.instrument_type})'


class InstrumentPrice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    instrument = models.ForeignKey(FinancialInstrument, on_delete=models.CASCADE, related_name='prices')
    price_date = models.DateField()
    price = models.DecimalField(max_digits=16, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=255, blank=True, default='')
    updated_by = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['instrument', 'price_date']
        verbose_name = 'Instrument Price'
        verbose_name_plural = 'Instrument Prices'
        unique_together = ['instrument', 'price_date']

    def __str__(self):
        return f'{self.instrument.instrument_code} @ {self.price_date}'


class PLLedger(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    month = models.CharField(max_length=7, help_text='YYYY-MM')
    revenue = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    opex = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    interest_expense = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    net_profit = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=255, blank=True, default='')
    updated_by = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['-month']
        verbose_name = 'P&L Ledger'
        verbose_name_plural = 'P&L Ledgers'
        unique_together = ['month']

    def __str__(self):
        return f'P&L {self.month}'


class NavHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nav_date = models.DateField()
    nav_per_unit = models.DecimalField(max_digits=14, decimal_places=4)
    total_units = models.DecimalField(max_digits=16, decimal_places=4)
    total_aum = models.DecimalField(max_digits=18, decimal_places=2)
    total_assets = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_liabilities = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    cash = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    loan_outstanding = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    outbound_valuation = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    management_fee_accrued = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    performance_fee_accrued = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=255, blank=True, default='')
    updated_by = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['-nav_date']
        verbose_name = 'NAV History'
        verbose_name_plural = 'NAV History'
        unique_together = ['nav_date']

    def __str__(self):
        return f'NAV {self.nav_date}'


class InvestorHolding(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    investor = models.ForeignKey(Investor, on_delete=models.CASCADE, related_name='holdings')
    units_held = models.DecimalField(max_digits=16, decimal_places=4, default=0)
    avg_cost_per_unit = models.DecimalField(max_digits=16, decimal_places=4, default=0)
    total_invested = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    current_value = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    unrealized_pl = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=255, blank=True, default='')
    updated_by = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Investor Holding'
        verbose_name_plural = 'Investor Holdings'
        unique_together = ['investor']

    def __str__(self):
        return f'{self.investor.name} - {self.units_held} units'


class FeeStructure(models.Model):
    FREQ_CHOICES = [('monthly', 'Monthly'), ('quarterly', 'Quarterly'), ('annual', 'Annual')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    management_fee_annual_pct = models.DecimalField(max_digits=6, decimal_places=2, default=2.00)
    performance_fee_pct = models.DecimalField(max_digits=6, decimal_places=2, default=20.00)
    hurdle_rate_pct = models.DecimalField(max_digits=6, decimal_places=2, default=5.00)
    high_water_mark = models.DecimalField(max_digits=16, decimal_places=4, default=0)
    fee_frequency = models.CharField(max_length=50, choices=FREQ_CHOICES, default='monthly')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=255, blank=True, default='')
    updated_by = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Fee Structure'
        verbose_name_plural = 'Fee Structures'

    def __str__(self):
        return f'Mgmt: {self.management_fee_annual_pct}%, Perf: {self.performance_fee_pct}%'


class FeeAccrual(models.Model):
    FEE_TYPES = [('management', 'Management'), ('performance', 'Performance')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    accrual_date = models.DateField()
    fee_type = models.CharField(max_length=50, choices=FEE_TYPES)
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    nav_before_fee = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    nav_after_fee = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    is_settled = models.BooleanField(default=False)
    settled_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=255, blank=True, default='')
    updated_by = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['-accrual_date']
        verbose_name = 'Fee Accrual'
        verbose_name_plural = 'Fee Accruals'

    def __str__(self):
        return f'{self.fee_type} - {self.amount} ({self.accrual_date})'


# ── Backward-compatible constants for serializers ─────────────

INVESTOR_CATEGORIES = [c[0] for c in Investor.CATEGORY_CHOICES]
KYC_STATUSES = [c[0] for c in Investor.KYC_CHOICES]
TRANSACTION_TYPES = [c[0] for c in Transaction.TX_TYPES]
PAYMENT_METHODS = [c[0] for c in Transaction.PAYMENT_METHODS]
TRANSACTION_STATUSES = [c[0] for c in Transaction.TX_STATUSES]
LOAN_STATUSES = [c[0] for c in Loan.LOAN_STATUSES]
LOAN_SCHEDULE_PAYMENT_STATUSES = [c[0] for c in LoanSchedule.PAYMENT_STATUSES]
OUTBOUND_ENTITY_TYPES = [c[0] for c in OutboundPlacement.ENTITY_TYPES]
OUTBOUND_STATUSES = [c[0] for c in OutboundPlacement.STATUSES]
INSTRUMENT_TYPES = [c[0] for c in FinancialInstrument.INSTRUMENT_TYPES]


class Counter(models.Model):
    """Simple counter for sequential code generation."""
    id = models.CharField(max_length=100, primary_key=True)
    value = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Counter'
        verbose_name_plural = 'Counters'
