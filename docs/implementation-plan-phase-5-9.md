# Investment Module — Enhancement Implementation Plan (Phases 5–9)

**Author**: Senior ERP Architect  
**Date**: 2026-07-10  
**Status**: Approved  
**Priority**: High (Phase 5-6) / Medium (Phase 7-8) / Low (Phase 9)

---

## Architecture Overview

All phases follow the existing architecture patterns:
- **Data**: MySQL tables via Django models in `models.py`
- **Services**: Business logic in `services.py`, database CRUD via Django ORM
- **Views**: Django views in `views.py` + REST ViewSets in `api/viewsets.py`
- **Reports**: Static methods in `reports.py`, Chart.js in `reports.html`
- **Tasks**: Celery `@shared_task` in `tasks.py`, registered in `config/settings.py`
- **API**: DRF serializers in `api/serializers.py`, router in `api/urls.py`

No new Python packages required beyond what is already installed (Django, DRF, Celery, Redis, mysqlclient, Chart.js CDN).

---

## Immediate Actions (Pre-Phase 5)

### I-1: Wire Up Instrument Price History

**Files affected**:
- `investment/api/urls.py`
- `investment/api/viewsets.py`
- `investment/api/serializers.py`
- `investment/views.py` (`instruments_list`)
- `investment/services.py` (model query already exists)
- `templates/investment/instruments.html`

**Changes**:

1. **`api/urls.py`** — Add `InstrumentPriceViewSet` to router:
```python
router.register(r'instrument-prices', InstrumentPriceViewSet, basename='investment-instrumentprice')
```

2. **`api/viewsets.py`** — Add `InstrumentPriceViewSet`:
```python
class InstrumentPriceViewSet(viewsets.ModelViewSet):
    queryset = InstrumentPrice.objects.all()
    serializer_class = InstrumentPriceSerializer
```

3. **`api/serializers.py`** — Add `InstrumentPriceSerializer`:
```python
class InstrumentPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstrumentPrice
        fields = '__all__'
```

4. **`views.py`** — In `instruments_list`, add price history edit/delete actions and pass prices to template context.

5. **`instrument.htmls`** — Add a price history section with:
   - Chart.js line chart (price over time) per instrument
   - Table of recent prices
   - Form to add new price point (in modal)

6. **`reports.py`** — In `instrument_performance()`, incorporate latest price from `InstrumentPrice` model to calculate market value:
```python
latest_prices = InstrumentPrice.objects.values('instrument_id').annotate(
    max_date=Max('price_date')
)
market_value = latest_price * units_outstanding
```

### I-2: Convert Monetary Fields to Decimal/String

**Files affected**:
- `investment/models.py` (all schema dataclasses)
- `investment/services.py` (`compute_pmt`, `generate_schedule` helpers)
- `investment/views.py` (all `float()` conversions)
- `investment/reports.py` (all `float()` aggregations)
- `investment/tests.py` (update test assertions)

**Strategy**:
- Monetary values are stored as **strings** with format `"1234.56"` (2 decimal places) to ensure precision across all operations.
- Add helper functions in `services.py`:

```python
def money_to_str(value) -> str:
    return f"{Decimal(str(value)):.2f}"

def money_to_float(value) -> float:
    if isinstance(value, str):
        return round(float(value), 2)
    return round(float(value), 2)

def money_add(*args) -> str:
    total = sum(Decimal(str(a)) for a in args)
    return f"{total:.2f}"
```

- All database reads convert string → Decimal internally.
- All database writes convert Decimal → string.

**Migration note**: Existing database records with `float` fields will be read via `money_to_float()` for backward compatibility. New writes use `money_to_str()`.

---

## Phase 5: NAV Engine, Unit Tracking & Fee Engine

**Priority**: Critical  
**Estimated effort**: 5-7 days  
**Validation**: NAV calculation must match manual computation within BDT 0.01 per 1,000 units.

### 5.1 New Schemas — `models.py`

```python
@dataclass
class NavSchema:
    """Table: invst_nav_history"""
    nav_date: str                          # YYYY-MM-DD
    nav_per_unit: str                       # stored as "123.4567" (4 decimal places)
    total_units: str                        # outstanding units
    total_aum: str                          # total assets under management
    management_fee_accrued: str = "0.00"
    performance_fee_accrued: str = "0.00"
    total_liabilities: str = "0.00"
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: str = ""
    updated_by: str = ""

@dataclass
class InvestorHoldingSchema:
    """Table: invst_investor_holdings"""
    investor_id: str
    units_held: str                         # "0.0000"
    avg_cost_per_unit: str = "0.0000"
    total_invested: str = "0.00"
    current_value: str = "0.00"
    unrealized_pl: str = "0.00"
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: str = ""
    updated_by: str = ""

@dataclass
class FeeStructureSchema:
    """Table: invst_fee_structures (singleton or per-fund)"""
    management_fee_annual_pct: str = "2.00"
    performance_fee_pct: str = "20.00"
    hurdle_rate_pct: str = "5.00"
    high_water_mark: str = "0.00"           # highest past NAV per unit
    fee_frequency: str = "monthly"          # monthly / quarterly / annual
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: str = ""
    updated_by: str = ""

@dataclass
class FeeAccrualSchema:
    """Table: invst_fee_accruals"""
    accrual_date: str                       # YYYY-MM-DD
    fee_type: str                           # management / performance
    amount: str
    nav_before_fee: str = "0.00"
    nav_after_fee: str = "0.00"
    is_settled: bool = False
    settled_date: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: str = ""
    updated_by: str = ""
```

### 5.2 Table Name Constants — `services.py`

```python
TABLE_NAV_HISTORY = 'invst_nav_history'
TABLE_INVESTOR_HOLDINGS = 'invst_investor_holdings'
TABLE_FEE_STRUCTURES = 'invst_fee_structures'
TABLE_FEE_ACCRUALS = 'invst_fee_accruals'
```

### 5.3 NAV Engine — `services.py`

```python
class NavService:
    """NAV calculation engine."""

    @staticmethod
    def calculate_nav(nav_date: date) -> dict:
        """Compute NAV per unit for a given date.
        
        NAV = (Total Assets - Total Liabilities) / Total Units Outstanding
        
        Total Assets = Cash (inflows - outflows + interest collected) 
                     + Loan Outstanding Principal 
                     + Outbound Current Valuations
        Total Liabilities = Unpaid Interest + Fee Accruals + Other Payables
        """
        # 1. Compute total assets
        #    - Cleared capital inflows
        #    - Outstanding loan principal (active loans)
        #    - Outbound current valuations (active placements)
        # 2. Compute total liabilities
        #    - Unpaid scheduled interest
        #    - Accrued but unpaid fees
        # 3. Compute total AUM = Assets - Liabilities
        # 4. Read total outstanding units from invst_investor_holdings (sum)
        # 5. NAV per unit = AUM / Total Units
        # 6. Determine high water mark from FeeStructureSchema
        # 7. Compute management fee: AUM * (annual_rate / 365) * days_since_last_nav
        # 8. Compute performance fee if NAV > high water mark
        # 9. Write to invst_nav_history
        # 10. Update each investor holding: units_held, current_value, unrealized_pl

    @staticmethod
    def issue_units(investor_id: str, amount: str, nav_per_unit: str) -> dict:
        """Issue new units at current NAV.
        
        Units = Investment Amount / NAV per Unit
        Updates InvestorHoldingSchema.
        """

    @staticmethod
    def redeem_units(investor_id: str, units: str, nav_per_unit: str) -> dict:
        """Redeem units at current NAV.
        
        Proceeds = Units * NAV per Unit
        Updates InvestorHoldingSchema.
        """
```

### 5.4 Fee Engine — `services.py`

```python
class FeeService:
    @staticmethod
    def calculate_management_fee(aum: str, annual_rate_pct: str, days: int) -> str:
        """Management fee = AUM * (annual_rate / 365) * days"""
        
    @staticmethod
    def calculate_performance_fee(
        current_nav: str, high_water_mark: str, 
        total_units: str, perf_fee_pct: str
    ) -> str:
        """Performance fee = (Current NAV - HWM) * Units * Fee%"""
```

### 5.5 Celery Task — `tasks.py`

```python
@shared_task
def calculate_daily_nav():
    """Run daily NAV calculation and fee accrual."""
    nav_date = date.today()
    result = NavService.calculate_nav(nav_date)
    return f"NAV computed: {result['nav_per_unit']} on {nav_date}"

@shared_task
def accrue_monthly_fees():
    """End-of-month fee accrual and settlement."""
    # 1. Calculate management fee for the month
    # 2. Calculate performance fee if applicable
    # 3. Write FeeAccrual records
    # 4. Adjust NAV
    # 5. Optionally transfer fees to firm account
```

### 5.6 Beat Schedule — `config/settings.py`

```python
'daily-nav-calculation': {
    'task': 'investment.tasks.calculate_daily_nav',
    'schedule': 86400,  # daily
},
'monthly-fee-accrual': {
    'task': 'investment.tasks.accrue_monthly_fees',
    'schedule': cron(hour=23, minute=59, day_of_month='last'),
},
```

### 5.7 API Endpoints — `api/urls.py`

```python
router.register(r'nav-history', NavHistoryViewSet, basename='investment-navhistory')
router.register(r'investor-holdings', InvestorHoldingViewSet, basename='investment-investorholding')
router.register(r'fee-structures', FeeStructureViewSet, basename='investment-feestructure')
router.register(r'fee-accruals', FeeAccrualViewSet, basename='investment-feeaccrual')
```

### 5.8 Views & Templates

**New views** (in `views.py`):
- `nav_dashboard(request)` — NAV trend chart, current NAV, units outstanding, AUM
- `investor_holdings_list(request)` — per-investor unit balance, value, P&L
- `fee_management(request)` — fee structure CRUD, accrual history

**New templates**:
- `templates/investment/nav.html`
- `templates/investment/holdings.html`
- `templates/investment/fees.html`

### 5.9 Reports Integration — `reports.py`

Add to `ReportService`:
```python
@staticmethod
def nav_summary():
    """NAV trend, AUM history, unit issuance/redemption activity."""

@staticmethod
def fee_impact():
    """Show cumulative fees deducted from returns."""
```

### 5.10 Tests — `tests.py`

New test classes:
- `NavCalculationTests` — mock database data, verify NAV math
- `FeeCalculationTests` — management fee, performance fee, high-water mark
- `UnitIssuanceTests` — unit math, holding updates
- `NavCeleryTaskTests` — mock task execution

---

## Phase 6: Performance Metrics & Price History Wiring

**Priority**: High  
**Estimated effort**: 3-5 days  
**Validation**: TWRR calculation must match Bloomberg/Reuters within 0.01%.

### 6.1 Performance Metrics Service — `services.py`

```python
class PerformanceService:
    @staticmethod
    def time_weighted_return(nav_series: list[dict]) -> float:
        """Compute TWRR using geometric linking of sub-period returns.
        
        R_sub = (NAV_t - NAV_t-1) / NAV_t-1
        TWRR = (1 + R_1) * (1 + R_2) * ... * (1 + R_n) - 1
        """
        
    @staticmethod
    def money_weighted_return(cash_flows: list[dict], final_value: float) -> float:
        """Compute IRR/MWRR using Newton-Raphson or Brent method.
        
        NPV = sum(CF_t / (1 + IRR)^t) = 0
        """
        
    @staticmethod
    def sharpe_ratio(returns: list[float], risk_free_rate: float = 0.05) -> float:
        """Sharpe = (R_p - R_f) / sigma_p"""
        
    @staticmethod
    def sortino_ratio(returns: list[float], risk_free_rate: float = 0.05, target: float = 0.0) -> float:
        """Sortino = (R_p - R_f) / downside_deviation"""
        
    @staticmethod
    def max_drawdown(nav_series: list[dict]) -> dict:
        """Maximum peak-to-trough decline.
        
        Returns: {'max_drawdown_pct': float, 'peak_date': str, 'trough_date': str}
        """
        
    @staticmethod
    def annualized_return(total_return: float, years: float) -> float:
        """CAGR = (1 + total_return)^(1/years) - 1"""
        
    @staticmethod
    def rolling_return(nav_series: list[dict], window_months: int = 12) -> list[dict]:
        """Rolling periodic returns for volatility analysis."""
```

### 6.2 ReportService Extension — `reports.py`

```python
@staticmethod
def performance_metrics(investor_id: str = None) -> dict:
    """Aggregate all performance metrics.
    
    Returns:
        - twrr (since inception)
        - mwrr / irr
        - sharpe_ratio
        - sortino_ratio
        - max_drawdown
        - cagr (1yr, 3yr, 5yr, since inception)
        - rolling_12m_returns
        - win_rate
        - volatility (annualized)
    """
```

### 6.3 Chart.js Additions — `reports.html`

New tab: **Performance Analytics** with:
- Equity curve (NAV over time) — line chart
- Drawdown chart — area chart (negative values)
- Rolling 12-month returns — bar chart
- Risk/return scatter plot (if multi-investor)
- KPI cards: Sharpe, Sortino, Max DD, CAGR, Volatility

### 6.4 CSV Export — `reports.py`

```python
def _export_performance_csv(response):
    """Per-investor or aggregate performance data."""
```

### 6.5 Price History Wiring (Continuation)

Already outlined in **I-1**. Complete wiring includes:
- `instruments.html` price chart with date range selector
- Filter: `?instrument_id=X&from=YYYY-MM-DD&to=YYYY-MM-DD`
- Price history API with pagination

### 6.6 Tests — `tests.py`

```python
class PerformanceMetricsTests(TestCase):
    def test_twrr_computation(self):
        """Verify TWRR against known series."""
    def test_sharpe_ratio_computation(self):
    def test_max_drawdown_identification(self):
    def test_cagr_computation(self):
    def test_rolling_return_window(self):
```

---

## Phase 7: Compliance, Currency Support & Decimal Precision

**Priority**: Medium  
**Estimated effort**: 4-6 days  
**Validation**: Compliance alerts fire correctly for known breach scenarios.

### 7.1 Decimal Precision (Surface)

Already detailed in **I-2**. Full conversion includes:
- Create `services.py` helper functions
- Replace all `float()` calls in `views.py` with `money_to_float()`
- Update all schema defaults to strings
- Add migration script `scripts/migrate_float_to_str.py` to convert existing records

### 7.2 Compliance Monitoring — `tasks.py` & `services.py`

```python
@shared_task
def check_kyc_expiry():
    """Flag investors with expired or soon-to-expire KYC.
    
    - Mark investors with KYC 'Expired' as is_active=False
    - Log warning for KYC expiring within 30 days
    - Create in-app notifications for compliance team
    """

@shared_task
def check_concentration_limits():
    """Alert if any investor exceeds concentration threshold.
    
    Concentration = Single Investor AUM / Total AUM
    Threshold: default 25% (configurable)
    """
    # For each investor holding:
    #   concentration = holding.current_value / nav_history[-1].total_aum
    #   if concentration > threshold → log alert

class ComplianceService:
    @staticmethod
    def investor_concentration(investor_id: str) -> dict:
        """Return concentration metrics for an investor."""
        
    @staticmethod
    def sector_concentration() -> dict:
        """Sector breakdown of loan portfolio."""
        
    @staticmethod
    def instrument_concentration() -> dict:
        """Instrument type concentration."""
        
    @staticmethod
    def kyc_compliance_report() -> list[dict]:
        """All investors with KYC status gaps."""
```

### 7.3 Beat Schedule Additions — `config/settings.py`

```python
'daily-kyc-expiry-check': {
    'task': 'investment.tasks.check_kyc_expiry',
    'schedule': 86400,
},
'weekly-concentration-check': {
    'task': 'investment.tasks.check_concentration_limits',
    'schedule': 604800,  # weekly
},
```

### 7.4 Compliance Dashboard — `reports.py` & `reports.html`

New tab: **Compliance** with:
- KYC status matrix (table by investor)
- Concentration pie charts (by investor, sector, instrument)
- Threshold breach alerts
- CSV export

### 7.5 Currency Support Foundation — `models.py`

```python
@dataclass
class CurrencyConfigSchema:
    """Table: invst_currency_config"""
    base_currency: str = "BDT"
    fx_rate_source: str = "manual"     # manual / api
    last_updated: Optional[str] = None

@dataclass
class FxRateSchema:
    """Table: invst_fx_rates"""
    from_currency: str
    to_currency: str
    rate: str                            # "1.0000" format
    rate_date: str
    is_active: bool = True
```

- All monetary schemas optionally extended with `currency: str = "BDT"` field
- Aggregation logic in `ReportService` applies FX conversion for multi-currency consolidation

---

## Phase 8: Cash Flow Forecasting & Scenario Modeling

**Priority**: Medium  
**Estimated effort**: 3-4 days  
**Validation**: Forecast error < 5% when back-tested against 3 months of actual data.

### 8.1 Forecast Engine — `services.py`

```python
class CashFlowForecastService:
    @staticmethod
    def forecast_payables(months_ahead: int = 12) -> list[dict]:
        """Project expected loan repayments from unpaid schedules.
        
        For each loan schedule with due_date in range:
            inflow = scheduled_principal + scheduled_interest
        Return monthly aggregation.
        """
        
    @staticmethod
    def forecast_outbound_calls(months_ahead: int = 12) -> list[dict]:
        """Project expected outbound capital requirements from active placements."""
        
    @staticmethod
    def forecast_nav_growth(months_ahead: int = 12, 
                             expected_return_pct: float = 10.0,
                             expected_inflows: list[dict] = None) -> list[dict]:
        """Project AUM and NAV based on expected returns and capital flows.
        
        Simple model:
            AUM_t = AUM_t-1 * (1 + r_monthly) + net_cash_flow_t - fees_t
        """
        
    @staticmethod
    def what_if_default_rate(base_default_rate: float = 0.02,
                              stress_default_rate: float = 0.10) -> dict:
        """Scenario: what if X% of loans default?
        
        Stress test AUM impact, cash flow shortfall.
        """
```

### 8.2 ReportService Extension — `reports.py`

```python
@staticmethod
def cash_flow_forecast(months: int = 12) -> dict:
    """Combined view: projected inflows (repayments) vs outflows (calls, expenses)."""
```

### 8.3 Reports Tab — `reports.html`

New tab: **Cash Flow Forecast** with:
- Stacked bar chart: Projected inflows vs outflows by month
- Line chart: Projected AUM growth
- KPI: Minimum cash balance, liquidity ratio
- Scenario inputs: default rate slider, expected return slider
- Table of assumptions

### 8.4 Tests — `tests.py`

```python
class CashFlowForecastTests(TestCase):
    def test_forecast_payables_projects_correct_months(self):
    def test_what_if_default_rate_reduces_aum(self):
    def test_nav_growth_with_expected_returns(self):
```

---

## Phase 9: Client Portal, PDF Statements & Automated Reporting

**Priority**: Low  
**Estimated effort**: 5-8 days  
**Validation**: Portal loads for test investor with <2s response time.

### 9.1 Investor Portal

**New app or module section**: `investment/portal_views.py`

- Investor login (separate auth or token-based)
- Dashboard: current holdings, investment value, recent transactions
- Statements: download PDF
- Profile: update contact info, upload KYC documents
- Activity log: all transactions, fee deductions, NAV changes

**Templates**:
- `templates/investment/portal/dashboard.html`
- `templates/investment/portal/statements.html`
- `templates/investment/portal/profile.html`

### 9.2 PDF Statement Generation

**New file**: `investment/pdf_service.py`

```python
class PdfStatementService:
    @staticmethod
    def generate_investor_statement(investor_id: str, period: str) -> bytes:
        """Generate PDF statement for an investor.
        
        Sections:
        1. Header (logo, date, investor info)
        2. Portfolio Summary (total invested, current value, return)
        3. Holdings Detail (units, NAV, value)
        4. Transaction History (period)
        5. Fee Summary
        6. Performance Metrics (since inception)
        7. Disclaimer
        
        Uses ReportLab (pip install reportlab) or WeasyPrint.
        """
        
    @staticmethod
    def generate_portfolio_report(period: str) -> bytes:
        """Generate firm-wide portfolio report."""
```

**Views**: `statement_download(request, investor_id, period)`

### 9.3 Automated Report Dispatch

**New Celery tasks**:
```python
@shared_task
def dispatch_monthly_statements():
    """Generate and email/portal monthly statements to all investors."""

@shared_task
def dispatch_weekly_performance_summary():
    """Email performance summary to management."""
```

**New service**: `notification_service.py` (or extend existing)
- Email dispatch via Django mail or SendGrid/Mailgun
- WhatsApp/SMS dispatch via Twilio or similar
- In-app notification (existing toast system)

### 9.4 Templates

- `templates/investment/portal/statement_pdf.html` (for WeasyPrint)
- `templates/investment/email/monthly_statement.html`
- `templates/investment/email/performance_summary.html`

### 9.5 API Endpoints

```python
# Investor portal API (token-authenticated)
router.register(r'portal/holdings', PortalHoldingViewSet, basename='portal-holdings')
router.register(r'portal/transactions', PortalTransactionViewSet, basename='portal-transactions')
router.register(r'portal/statements', PortalStatementViewSet, basename='portal-statements')
```

---

## Migration & Deployment Plan

### Data Migration

For each phase involving new tables or schema changes:

1. **Create script**: `investment/scripts/migrate_<feature>.py`
2. **Script pattern**:
   - Read existing records from source table
   - Transform data (float→string, add new fields)
   - Write to new table
   - Log summary: count migrated, errors
3. **Safety**: All migrations are idempotent — safe to re-run

### Database Indexes

New composite indexes required (created via Django model `Meta.indexes` or `migrations.AddIndex`):

| Table | Fields | Use Case |
|-----------|--------|----------|
| `invst_nav_history` | `nav_date` DESC | Latest NAV query |
| `invst_investor_holdings` | `investor_id` | Per-investor lookup |
| `invst_instrument_prices` | `instrument_id`, `price_date` DESC | Latest price per instrument |
| `invst_fee_accruals` | `fee_type`, `accrual_date` DESC | Fee history |
| `invst_fx_rates` | `from_currency`, `to_currency`, `rate_date` DESC | Latest rate |

### Rollout Strategy

| Phase | Deploy Window | Rollback Mechanism |
|-------|--------------|--------------------|
| I-1, I-2 | Sprint 1 | Revert database data via backup |
| Phase 5 | Sprint 2-3 | `invst_nav_history` is append-only; disable task |
| Phase 6 | Sprint 3-4 | `PerformanceService` is additive; remove from reports |
| Phase 7 | Sprint 4 | Compliance tasks are log-only initially |
| Phase 8 | Sprint 5 | Forecast is advisory; no data written |
| Phase 9 | Sprint 6+ | Portal is separate URL namespace |

### Testing Strategy

| Phase | Test Focus | Coverage Target |
|-------|-----------|-----------------|
| I-1 | API CRUD, price chart rendering | 90%+ |
| I-2 | Monetary precision, float→str conversion | 100% edge cases |
| 5 | NAV math, fee math, unit issuance math | 100% |
| 6 | TWRR, Sharpe, max drawdown calculations | 100% |
| 7 | Compliance thresholds, KYC expiry logic | 95% |
| 8 | Forecast projections, scenario assumptions | 90% |
| 9 | PDF output, portal auth, scheduled dispatch | 85% |

---

## File Inventory — All Changes by Phase

| File | I-1 | I-2 | P5 | P6 | P7 | P8 | P9 |
|------|-----|-----|----|----|----|----|----|
| `investment/models.py` | | X | X | | X | | |
| `investment/services.py` | X | X | X | X | X | X | |
| `investment/views.py` | X | X | X | | | | X |
| `investment/reports.py` | X | X | X | X | X | X | |
| `investment/tasks.py` | | | X | | X | | X |
| `investment/tests.py` | X | X | X | X | X | X | X |
| `investment/api/serializers.py` | X | | X | | X | | X |
| `investment/api/viewsets.py` | X | | X | | X | | X |
| `investment/api/urls.py` | X | | X | | X | | X |
| `investment/pdf_service.py` | | | | | | | NEW |
| `investment/portal_views.py` | | | | | | | NEW |
| `config/settings.py` | | | X | | X | | X |
| `templates/investment/instruments.html` | X | | | X | | | |
| `templates/investment/reports.html` | X | | X | X | X | X | |
| `templates/investment/nav.html` | | | NEW | | | | |
| `templates/investment/holdings.html` | | | NEW | | | | |
| `templates/investment/fees.html` | | | NEW | | | | |
| `templates/investment/portal/*.html` | | | | | | | NEW |
| `templates/investment/email/*.html` | | | | | | | NEW |

---

## Architecture Decisions & Trade-offs

### Why MySQL for NAV
- NAV calculations are read-heavy (all holdings, all loans, all transactions) — MySQL handles concurrent reads efficiently
- Aggregation queries use Django ORM annotations and aggregations for optimal performance
- Django ORM provides atomic transactions for consistent concurrent unit issuance and fee accrual
- **Trade-off**: Requires careful index design on high-volume queries

### Why string-based monetary storage
- Django DecimalField is used at the model level, but string serialization ensures precision across API, reports, and CSV exports
- String format guarantees exact decimal representation during JSON serialization (avoiding float64 precision loss)
- **Trade-off**: Requires conversion helper functions; slight read/write overhead

### Why TWRR over IRR/MWRR for default reporting
- TWRR eliminates the impact of capital flows, showing pure manager performance
- IRR is investor-specific (depends on timing of their cash flows)
- **Decision**: Show TWRR as primary metric, MWRR as supplemental per-investor metric

### Why separate tables over embedded models
- NAV history, holdings, and fee accruals need cross-investor queries (e.g., "total AUM")
- Django ORM handles joins and aggregation across tables efficiently
- **Decision**: Separate tables with foreign key references for all entities

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Database query performance at scale | Low | High | Implement pagination in all list views; add Redis caching layer for NAV data |
| Concurrent unit issuance race condition | Medium | Medium | Use Django ORM `select_for_update()` and `atomic()` transactions for issue/redeem operations |
| Fee calculation disputes with investors | Medium | High | Maintain full audit trail in `FeeAccrualSchema`; add independent calculation verification task |
| Performance fee high-water mark rollback | Low | High | HWM is append-only; never update in place — always write new record with reference to previous |

---

## Conclusion

The six-phase plan (Immediate + Phases 5-9) transforms the current loan-and-investor tracking system into a complete **investment management platform** with institutional-grade capabilities:

1. **NAV & Unit Engine** (P5) — enables fund operations
2. **Performance Analytics** (P6) — enables institutional reporting
3. **Compliance & Precision** (P7) — enables regulatory readiness  
4. **Forecasting** (P8) — enables strategic planning
5. **Client Portal & PDF** (P9) — enables investor self-service

Each phase is independently deployable, backward-compatible with existing database data, and follows the established architecture patterns. Recommend prioritizing I-1, I-2, and Phase 5 as the critical path to unblock fund operations.
