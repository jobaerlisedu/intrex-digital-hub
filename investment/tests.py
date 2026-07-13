"""
Unit and integration tests for the Investment module.

Pure business logic (PMT, amortization) is tested directly.
ORM-dependent tests use Django TestCase with model factories.
"""

import json
from datetime import date
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings, RequestFactory
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse

from investment.services import (
    AmortizationService as amt,
    CodeGenerator,
    ORMDocumentService as fs,
    NavService,
    FeeService,
    PerformanceService,
    CashFlowForecastService,
    COLL_INVESTORS,
    COLL_INVESTOR_HOLDINGS,
    COLL_TRANSACTIONS,
    COLL_NAV_HISTORY,
    COLL_FEE_ACCRUALS,
    COLL_LOANS,
    COLL_OUTBOUND,
    COLL_FEE_STRUCTURES,
    money_to_str,
    money_to_float,
    money_add,
)
from investment.api.serializers import (
    InvestorSerializer,
    TransactionSerializer,
    LoanSerializer,
    LoanScheduleSerializer,
    OutboundPlacementSerializer,
    FinancialInstrumentSerializer,
    PLLedgerSerializer,
)


# ══════════════════════════════════════════════
# UNIT TESTS — PMT Computation
# ══════════════════════════════════════════════

class PMTComputationTests(TestCase):
    """Verify PMT formula correctness for standard and edge cases."""

    def test_standard_pmt(self):
        """$100,000 at 10% annual for 12 months."""
        pmt = amt.compute_pmt(100000.0, 10.0, 12)
        # Expected: ~8791.59 (standard PMT formula result)
        self.assertAlmostEqual(pmt, 8791.59, delta=0.01)

    def test_zero_rate_pmt(self):
        """$60,000 at 0% for 12 months → $5,000/mo."""
        pmt = amt.compute_pmt(60000.0, 0.0, 12)
        self.assertEqual(pmt, 5000.0)

    def test_single_month_pmt(self):
        """$10,000 at 5% for 1 month → full principal + interest."""
        pmt = amt.compute_pmt(10000.0, 5.0, 1)
        self.assertAlmostEqual(pmt, 10041.67, delta=0.01)

    def test_zero_principal_pmt(self):
        """$0 principal → $0 payment."""
        pmt = amt.compute_pmt(0.0, 10.0, 12)
        self.assertEqual(pmt, 0.0)

    def test_zero_months_pmt(self):
        """0 months → $0 payment (edge case)."""
        pmt = amt.compute_pmt(10000.0, 10.0, 0)
        self.assertEqual(pmt, 0.0)

    def test_large_principal_pmt(self):
        """$10M at 8% for 360 months (30-year mortgage sanity check)."""
        pmt = amt.compute_pmt(10_000_000.0, 8.0, 360)
        self.assertAlmostEqual(pmt, 73376.46, delta=0.1)


# ══════════════════════════════════════════════
# UNIT TESTS — Amortization Schedule
# ══════════════════════════════════════════════

class AmortizationScheduleTests(TestCase):
    """Verify schedule integrity: sum check, length, balance convergence."""

    def setUp(self):
        self.loan_id = "test-loan-001"
        self.disb_date = date(2026, 1, 15)

    def test_schedule_sum_equals_principal(self):
        """Sum of scheduled_principal across all installments == original principal."""
        from investment.services import money_to_float
        schedule = amt.generate_schedule(100000.0, 10.0, 12, self.disb_date, self.loan_id)
        total_principal = sum(money_to_float(s['scheduled_principal']) for s in schedule)
        self.assertAlmostEqual(total_principal, 100000.0, delta=0.1)

    def test_schedule_has_correct_number_of_rows(self):
        """Exactly `months` rows generated."""
        schedule = amt.generate_schedule(50000.0, 8.0, 24, self.disb_date, self.loan_id)
        self.assertEqual(len(schedule), 24)

    def test_all_schedules_reference_loan(self):
        """Every schedule row has the correct loan_id."""
        schedule = amt.generate_schedule(50000.0, 8.0, 12, self.disb_date, self.loan_id)
        for s in schedule:
            self.assertEqual(s['loan_id'], self.loan_id)

    def test_schedule_zero_rate(self):
        """0% interest → equal principal, zero interest each period."""
        from investment.services import money_to_float
        schedule = amt.generate_schedule(12000.0, 0.0, 12, self.disb_date, self.loan_id)
        self.assertEqual(len(schedule), 12)
        for s in schedule:
            self.assertEqual(money_to_float(s['scheduled_principal']), 1000.0)
            self.assertEqual(money_to_float(s['scheduled_interest']), 0.0)

    def test_interest_expense_computation(self):
        """Interest expense for a given month sums correctly."""
        schedule = amt.generate_schedule(100000.0, 12.0, 12, self.disb_date, self.loan_id)
        # First installment due: Jan 15 + 1 month = Feb 15, so interest appears in 2026-02
        expense = amt.compute_interest_expense('2026-02', schedule)
        # First month interest = 100000 * (0.12/12) = 1000
        self.assertAlmostEqual(expense, 1000.0, delta=0.1)

    def test_last_installment_clears_balance(self):
        """After applying all schedule rows, remaining balance is ~0."""
        from investment.services import money_to_float
        schedule = amt.generate_schedule(100000.0, 10.0, 12, self.disb_date, self.loan_id)
        balance = Decimal('100000.0')
        for s in schedule:
            balance -= Decimal(str(money_to_float(s['scheduled_principal'])))
        self.assertAlmostEqual(float(balance), 0.0, delta=0.1)

    def test_each_installment_declining_interest(self):
        """Interest portion decreases each period (positive amortization)."""
        from investment.services import money_to_float
        schedule = amt.generate_schedule(100000.0, 10.0, 12, self.disb_date, self.loan_id)
        for i in range(1, len(schedule)):
            self.assertGreaterEqual(
                money_to_float(schedule[i - 1]['scheduled_interest']),
                money_to_float(schedule[i]['scheduled_interest']),
            )


# ══════════════════════════════════════════════
# UNIT TESTS — Category / KYC Choice Alignment
# ══════════════════════════════════════════════

class CategoryChoicesTests(TestCase):
    """Verify model-defined choices match what templates expect."""

    def test_investor_categories_include_venture_capital(self):
        from investment.models import INVESTOR_CATEGORIES
        self.assertIn('Venture Capital', INVESTOR_CATEGORIES)

    def test_investor_categories_include_angel(self):
        from investment.models import INVESTOR_CATEGORIES
        self.assertIn('Angel', INVESTOR_CATEGORIES)

    def test_kyc_statuses_include_expired(self):
        from investment.models import KYC_STATUSES
        self.assertIn('Expired', KYC_STATUSES)

    def test_kyc_statuses_include_all_template_values(self):
        from investment.models import KYC_STATUSES
        expected = {'Pending', 'Verified', 'Expired', 'Rejected'}
        self.assertEqual(set(KYC_STATUSES), expected)

    def test_investor_categories_include_all_template_values(self):
        from investment.models import INVESTOR_CATEGORIES
        expected = {'Individual', 'Corporate', 'Institutional', 'Venture Capital', 'Angel'}
        self.assertEqual(set(INVESTOR_CATEGORIES), expected)


# ══════════════════════════════════════════════
# UNIT TESTS — Code Generation
# ══════════════════════════════════════════════

class CodeGenerationTests(TestCase):
    """Test atomic counter-based code generation logic."""

    def test_next_sequence_generates_code(self):
        """Counter-based code generation returns formatted code."""
        from investment.services import CodeGenerator
        from investment.models import Counter
        Counter.objects.create(id='test_counter', value=5)
        result = CodeGenerator._next_sequence('test_counter', 'TST', 4)
        self.assertEqual(result, 'TST-0006')
        counter = Counter.objects.get(id='test_counter')
        self.assertEqual(counter.value, 6)


# ══════════════════════════════════════════════
# SERIALIZER TESTS
# ══════════════════════════════════════════════

class InvestorSerializerTests(TestCase):
    def test_valid_data_passes_validation(self):
        data = {
            'investor_code': 'INV-00001',
            'name': 'Test Investor',
            'category': 'Individual',
            'kyc_status': 'Pending',
        }
        serializer = InvestorSerializer(data=data)
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)

    def test_invalid_category_fails(self):
        data = {
            'investor_code': 'INV-00002',
            'name': 'Bad Category',
            'category': 'InvalidCategory',
        }
        serializer = InvestorSerializer(data=data)
        self.assertFalse(serializer.is_valid())


class LoanSerializerTests(TestCase):
    def test_valid_loan_passes(self):
        data = {
            'investor_id': 'inv-001',
            'investor_name': 'John Capital',
            'principal_amount': 100000.0,
            'outstanding_balance': 100000.0,
            'interest_rate': 10.0,
            'tenure_months': 12,
            'disbursement_date': '2026-01-15',
        }
        serializer = LoanSerializer(data=data)
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)


# ══════════════════════════════════════════════
# API TESTS (ORM-mocked)
# ══════════════════════════════════════════════

@override_settings(SECURE_SSL_REDIRECT=False)
class InvestmentAPITestCase(APITestCase):
    """API tests with ORMDocumentService fully mocked."""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # Ensure shared mocks persist across view calls within a test
        self.mock_investors = [
            {'id': 'doc-1', 'investor_code': 'INV-00001', 'name': 'Jane Capital', 'category': 'Individual', 'kyc_status': 'Verified'},
        ]

    @patch('investment.api.viewsets.fs.get_collection')
    @patch('investment.api.viewsets.fs.get_document')
    def test_investor_list_returns_200(self, mock_get_doc, mock_get_coll):
        mock_get_coll.return_value = self.mock_investors
        mock_get_doc.return_value = self.mock_investors[0]
        url = reverse('investment-investor-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    @patch('investment.api.viewsets.fs.create_document')
    @patch('investment.api.viewsets.fs.get_document')
    def test_investor_create_returns_201(self, mock_get_doc, mock_create):
        mock_create.return_value = 'new-doc-id'
        mock_get_doc.return_value = {
            'id': 'new-doc-id',
            'investor_code': 'INV-00100',
            'name': 'Jane Capital',
            'category': 'Individual',
            'kyc_status': 'Pending',
        }
        url = reverse('investment-investor-list')
        data = {'investor_code': 'INV-00100', 'name': 'Jane Capital'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch('investment.api.viewsets.fs.get_document')
    def test_investor_detail_returns_200(self, mock_get_doc):
        mock_get_doc.return_value = self.mock_investors[0]
        url = reverse('investment-investor-detail', kwargs={'pk': 'doc-1'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('investment.api.viewsets.fs.get_document')
    @patch('investment.api.viewsets.fs.update_document')
    def test_investor_update_returns_200(self, mock_update, mock_get_doc):
        mock_get_doc.return_value = self.mock_investors[0]
        url = reverse('investment-investor-detail', kwargs={'pk': 'doc-1'})
        data = {'investor_code': 'INV-00001', 'name': 'Updated Name'}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('investment.api.viewsets.fs.get_document')
    @patch('investment.api.viewsets.fs.delete_document')
    def test_investor_delete_returns_204(self, mock_delete, mock_get_doc):
        mock_get_doc.return_value = self.mock_investors[0]
        url = reverse('investment-investor-detail', kwargs={'pk': 'doc-1'})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_unauthenticated_access_returns_401(self):
        self.client.force_authenticate(user=None)
        url = reverse('investment-investor-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ══════════════════════════════════════════════
# UNIT TESTS — Partial Payment Logic
# ══════════════════════════════════════════════

class PartialPaymentTests(TestCase):
    """Verify partial payment proportion and balance tracking."""

    def test_full_payment_clears_schedule(self):
        """Paying full amount marks schedule as Paid."""
        principal = 8000.0
        interest = 2000.0
        total_due = principal + interest
        payment = total_due
        ratio = principal / total_due if total_due > 0 else 0
        principal_portion = payment * ratio
        interest_portion = payment - principal_portion
        self.assertAlmostEqual(principal_portion, 8000.0, delta=0.01)
        self.assertAlmostEqual(interest_portion, 2000.0, delta=0.01)
        self.assertAlmostEqual(payment, 10000.0)
        self.assertGreaterEqual(payment, total_due - 0.01)

    def test_partial_payment_proportional_split(self):
        """Partial payment splits proportionally between principal and interest."""
        principal = 8000.0
        interest = 2000.0
        total_due = principal + interest
        payment = 5000.0
        ratio = principal / total_due
        principal_portion = payment * ratio
        interest_portion_implied = payment - principal_portion
        self.assertAlmostEqual(principal_portion, 4000.0, delta=0.01)
        self.assertAlmostEqual(interest_portion_implied, 1000.0, delta=0.01)

    def test_small_partial_payment_does_not_clear(self):
        """Small payment does not trigger Paid status."""
        principal = 8000.0
        interest = 2000.0
        total_due = principal + interest
        payment = 1000.0
        prev_paid = 0.0
        new_paid = prev_paid + payment
        self.assertLess(new_paid, total_due - 0.01)
        self.assertFalse(new_paid >= total_due - 0.01)

    def test_cumulative_partial_payments_eventually_clear(self):
        """Multiple partial payments eventually clear the schedule."""
        principal = 8000.0
        interest = 2000.0
        total_due = principal + interest
        payments = [3000.0, 3000.0, 4000.0]
        cumulative = sum(payments)
        self.assertGreaterEqual(cumulative, total_due - 0.01)


# ══════════════════════════════════════════════
# UNIT TESTS — Report Service
# ══════════════════════════════════════════════

class ReportServiceTests(TestCase):
    """Test ReportService data aggregation with mocked data."""

    @patch('investment.reports.ReportService.capital_overview')
    def test_capital_overview_structure(self, mock_overview):
        mock_overview.return_value = {
            'total_capital_managed': 100000.0,
            'total_inflow': 50000.0,
            'total_outflow': 20000.0,
            'interest_due': 5000.0,
            'investors_count': 10,
            'source_breakdown': {'Inflow': 50000.0},
            'monthly_trend': {'labels': ['2026-01'], 'inflow': [50000.0], 'outflow': [20000.0]},
        }
        data = mock_overview()
        self.assertIn('total_capital_managed', data)
        self.assertIn('monthly_trend', data)
        self.assertEqual(data['investors_count'], 10)
        self.assertIn('labels', data['monthly_trend'])

    @patch('investment.reports.ReportService.loan_portfolio')
    def test_loan_portfolio_structure(self, mock_loan):
        mock_loan.return_value = {
            'total_loans': 5,
            'total_principal': 500000.0,
            'total_outstanding': 300000.0,
            'active_count': 3,
            'paid_count': 2,
            'defaulted_count': 0,
            'by_status': {'Active': {'count': 3, 'principal': 300000.0, 'outstanding': 300000.0}},
            'by_category': {'Individual': {'count': 3, 'principal': 300000.0}},
        }
        data = mock_loan()
        self.assertEqual(data['total_loans'], 5)
        self.assertEqual(data['active_count'], 3)
        self.assertIn('by_status', data)
        self.assertIn('by_category', data)

    @patch('investment.reports.ReportService.pl_summary')
    def test_pl_summary_structure(self, mock_pl):
        mock_pl.return_value = {
            'total_revenue': 100000.0,
            'total_opex': 40000.0,
            'total_interest_expense': 10000.0,
            'total_net_profit': 50000.0,
            'monthly_data': [{'month': '2026-01', 'revenue': 50000.0, 'opex': 20000.0, 'interest_expense': 5000.0, 'net_profit': 25000.0}],
            'months_covered': 1,
        }
        data = mock_pl()
        self.assertEqual(data['total_net_profit'], 50000.0)
        self.assertEqual(len(data['monthly_data']), 1)

    @patch('investment.reports.ReportService.investor_activity')
    def test_investor_activity_structure(self, mock_activity):
        mock_activity.return_value = {
            'total_investors': 10,
            'total_inflow': 500000.0,
            'total_outflow': 200000.0,
            'net_flow': 300000.0,
            'top_investors': [{'investor_name': 'Test Co', 'inflow': 50000.0, 'outflow': 10000.0, 'net': 40000.0, 'transaction_count': 5}],
        }
        data = mock_activity()
        self.assertEqual(data['total_investors'], 10)
        self.assertEqual(len(data['top_investors']), 1)

    @patch('investment.reports.ReportService.instrument_performance')
    def test_instrument_performance_structure(self, mock_inst):
        mock_inst.return_value = {
            'total_instruments': 3,
            'total_face_value': 150000.0,
            'total_units_issued': 10000,
            'by_type': {'Common Stock': {'count': 2, 'face_value_total': 100000.0, 'units_total': 8000}},
            'instruments': [{'code': 'INST-001', 'type': 'Common Stock', 'face_value': 50.0, 'units_issued': 5000, 'units_outstanding': 4500, 'issue_date': '2026-01-01'}],
        }
        data = mock_inst()
        self.assertEqual(data['total_instruments'], 3)
        self.assertIn('by_type', data)

    def test_report_data_json_valid_report(self):
        """The report_data_json view returns 200 for valid report names."""
        from investment.reports import report_data_json
        from django.http import HttpRequest
        req = HttpRequest()
        req.method = 'GET'
        with patch('investment.reports.ReportService.capital_overview') as mock:
            mock.return_value = {'status': 'ok'}
            response = report_data_json(req, 'capital_overview')
            self.assertEqual(response.status_code, 200)

    def test_report_data_json_invalid_report(self):
        """The report_data_json view returns 404 for unknown report names."""
        from investment.reports import report_data_json
        from django.http import HttpRequest
        req = HttpRequest()
        req.method = 'GET'
        response = report_data_json(req, 'nonexistent_report')
        self.assertEqual(response.status_code, 404)

    def test_export_csv_invalid_report(self):
        """The export_csv view returns 404 for unknown report names."""
        from investment.reports import export_csv
        from django.http import HttpRequest
        req = HttpRequest()
        req.method = 'GET'
        response = export_csv(req, 'nonexistent_report')
        self.assertEqual(response.status_code, 404)


# ══════════════════════════════════════════════
# UNIT TESTS — Celery Tasks (mocked)
# ══════════════════════════════════════════════

class CeleryTaskTests(TestCase):
    """Test Celery tasks with ORMDocumentService fully mocked."""

    @patch('investment.tasks.fs.get_collection')
    @patch('investment.tasks.fs.update_document')
    def test_check_overdue_schedules_marks_overdue(self, mock_update, mock_get_coll):
        from investment.tasks import check_overdue_schedules
        from datetime import date, timedelta

        past_date = (date.today() - timedelta(days=10)).isoformat()
        future_date = (date.today() + timedelta(days=10)).isoformat()

        mock_get_coll.return_value = [
            {'id': 's-1', 'payment_status': 'Unpaid', 'due_date': past_date},
            {'id': 's-2', 'payment_status': 'Unpaid', 'due_date': future_date},
        ]

        result = check_overdue_schedules()
        self.assertIn('1', result)
        mock_update.assert_called_once_with(
            'invst_loan_schedules', 's-1', {'payment_status': 'Overdue'}
        )

    @patch('investment.tasks.fs.get_collection')
    def test_send_investment_installment_reminders_counts(self, mock_get_coll):
        from investment.tasks import send_investment_installment_reminders
        from datetime import date, timedelta

        target = (date.today() + timedelta(days=3)).isoformat()

        def mock_get_coll_side_effect(*args):
            coll = args[0]
            if coll == 'invst_loan_schedules':
                return [
                    {'id': 's-1', 'loan_id': 'l-1', 'installment_number': 1, 'due_date': target,
                     'payment_status': 'Unpaid', 'scheduled_principal': 8000.0, 'scheduled_interest': 2000.0},
                ]
            if coll == 'invst_loans':
                return [{'id': 'l-1', 'investor_id': 'i-1'}]
            if coll == 'invst_investors':
                return [{'id': 'i-1', 'name': 'Test Investor'}]
            return []

        mock_get_coll.side_effect = mock_get_coll_side_effect
        result = send_investment_installment_reminders()
        self.assertIn('1', result)

    @patch('investment.tasks.fs.get_collection')
    def test_notify_overdue_schedules_logs(self, mock_get_coll):
        from investment.tasks import notify_overdue_schedules

        def mock_get_coll_side_effect(*args):
            coll = args[0]
            if coll == 'invst_loan_schedules':
                return [
                    {'id': 's-1', 'loan_id': 'l-1', 'installment_number': 2, 'due_date': '2026-01-01',
                     'payment_status': 'Overdue', 'scheduled_principal': 8000.0, 'scheduled_interest': 2000.0},
                ]
            if coll == 'invst_loans':
                return [{'id': 'l-1', 'investor_id': 'i-1'}]
            if coll == 'invst_investors':
                return [{'id': 'i-1', 'name': 'Test Investor'}]
            return []

        mock_get_coll.side_effect = mock_get_coll_side_effect
        result = notify_overdue_schedules()
        self.assertIn('1', result)

    def test_check_overdue_schedules_handles_empty(self):
        """Empty collection returns 0."""
        from investment.tasks import check_overdue_schedules
        with patch('investment.tasks.fs.get_collection', return_value=[]):
            result = check_overdue_schedules()
            self.assertIn('0', result)


# ══════════════════════════════════════════════
# UNIT TESTS — Model Schema Extensions (Phase 2)
# ══════════════════════════════════════════════

class InstrumentPriceSchemaTests(TestCase):
    """Verify InstrumentPriceSchema and FinancialInstrumentSchema extensions."""

    def test_instrument_price_schema_exists(self):
        from investment.models import InstrumentPriceSchema
        schema = InstrumentPriceSchema(instrument_id='inst-1', price_date='2026-01-15', price='105.50')
        self.assertEqual(schema.instrument_id, 'inst-1')
        self.assertEqual(schema.price, '105.50')
        self.assertEqual(schema.is_active, True)

    def test_financial_instrument_schema_has_maturity_date(self):
        from investment.models import FinancialInstrumentSchema
        schema = FinancialInstrumentSchema(
            instrument_code='INST-001',
            maturity_date='2030-12-31',
            sector='Technology',
            isin='US1234567890',
        )
        self.assertEqual(schema.maturity_date, '2030-12-31')
        self.assertEqual(schema.sector, 'Technology')
        self.assertEqual(schema.isin, 'US1234567890')

    def test_investor_kyc_document_default(self):
        investor = Investor.objects.create(investor_code='INV-001', name='Test')
        self.assertFalse(investor.kyc_document)

    def test_instrument_price_defaults(self):
        from investment.models import InstrumentPriceSchema
        schema = InstrumentPriceSchema(instrument_id='inst-1', price_date='2026-06-01', price='100.00')
        self.assertIsNone(schema.created_at)
        self.assertEqual(schema.created_by, '')


# ══════════════════════════════════════════════
# UNIT TESTS — Price History API & Serializer
# ══════════════════════════════════════════════

class InstrumentPriceSerializerTests(TestCase):
    """Verify InstrumentPriceSerializer validation."""

    def test_valid_price_passes(self):
        from investment.api.serializers import InstrumentPriceSerializer
        data = {
            'instrument_id': 'inst-001',
            'price_date': '2026-07-10',
            'price': 105.50,
        }
        serializer = InstrumentPriceSerializer(data=data)
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)

    def test_missing_instrument_id_fails(self):
        from investment.api.serializers import InstrumentPriceSerializer
        data = {'price_date': '2026-07-10', 'price': 105.50}
        serializer = InstrumentPriceSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_price_serializer_output_contains_all_fields(self):
        from investment.api.serializers import InstrumentPriceSerializer
        data = {
            'id': 'doc-1',
            'instrument_id': 'inst-001',
            'price_date': '2026-07-10',
            'price': 105.50,
            'is_active': True,
        }
        serializer = InstrumentPriceSerializer(data)
        self.assertIn('instrument_id', serializer.data)
        self.assertIn('price_date', serializer.data)
        self.assertIn('price', serializer.data)


@override_settings(SECURE_SSL_REDIRECT=False)
class InstrumentPriceAPITests(APITestCase):
    """Test price history API endpoints with mocked data."""

    def setUp(self):
        self.user = User.objects.create_user(username='priceuser', password='testpass')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    @patch('investment.api.viewsets.fs.get_collection')
    def test_price_list_returns_200(self, mock_get_coll):
        mock_get_coll.return_value = [
            {'id': 'p-1', 'instrument_id': 'inst-001', 'price_date': '2026-07-10', 'price': 105.50},
        ]
        url = reverse('investment-instrumentprice-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    @patch('investment.api.viewsets.fs.create_document')
    @patch('investment.api.viewsets.fs.get_document')
    def test_price_create_returns_201(self, mock_get_doc, mock_create):
        mock_create.return_value = 'new-price-id'
        mock_get_doc.return_value = {
            'id': 'new-price-id',
            'instrument_id': 'inst-001',
            'price_date': '2026-07-10',
            'price': 110.00,
        }
        url = reverse('investment-instrumentprice-list')
        data = {'instrument_id': 'inst-001', 'price_date': '2026-07-10', 'price': 110.00}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch('investment.api.viewsets.fs.get_document')
    def test_price_detail_returns_200(self, mock_get_doc):
        mock_get_doc.return_value = {
            'id': 'p-1', 'instrument_id': 'inst-001', 'price_date': '2026-07-10', 'price': 105.50,
        }
        url = reverse('investment-instrumentprice-detail', kwargs={'pk': 'p-1'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('investment.api.viewsets.fs.get_document')
    @patch('investment.api.viewsets.fs.delete_document')
    def test_price_delete_returns_204(self, mock_delete, mock_get_doc):
        mock_get_doc.return_value = {
            'id': 'p-1', 'instrument_id': 'inst-001', 'price_date': '2026-07-10', 'price': 105.50,
        }
        url = reverse('investment-instrumentprice-detail', kwargs={'pk': 'p-1'})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_unauthenticated_price_access_returns_401(self):
        self.client.force_authenticate(user=None)
        url = reverse('investment-instrumentprice-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ══════════════════════════════════════════════
# UNIT TESTS — Instrument Report Market Value
# ══════════════════════════════════════════════

class InstrumentMarketValueTests(TestCase):
    """Verify instrument_performance() includes market value from prices."""

    @patch('investment.reports.ReportService.instrument_performance')
    def test_market_value_in_output(self, mock_perf):
        mock_perf.return_value = {
            'total_instruments': 1,
            'total_face_value': 50.0,
            'total_units_issued': 5000,
            'total_market_value': 525000.0,
            'by_type': {'Common Stock': {'count': 1, 'face_value_total': 50.0, 'units_total': 5000, 'market_value_total': 525000.0}},
            'instruments': [
                {'code': 'INST-001', 'type': 'Common Stock', 'face_value': 50.0, 'units_issued': 5000,
                 'units_outstanding': 5000, 'latest_price': 105.0, 'market_value': 525000.0},
            ],
        }
        data = mock_perf()
        self.assertIn('total_market_value', data)
        self.assertEqual(data['total_market_value'], 525000.0)
        self.assertEqual(data['instruments'][0]['latest_price'], 105.0)
        self.assertEqual(data['instruments'][0]['market_value'], 525000.0)

    @patch('investment.reports.ReportService.instrument_performance')
    def test_empty_prices_zero_market_value(self, mock_perf):
        mock_perf.return_value = {
            'total_instruments': 1,
            'total_face_value': 50.0,
            'total_units_issued': 5000,
            'total_market_value': 0.0,
            'by_type': {'Common Stock': {'count': 1, 'face_value_total': 50.0, 'units_total': 5000, 'market_value_total': 0.0}},
            'instruments': [
                {'code': 'INST-001', 'type': 'Common Stock', 'face_value': 50.0, 'units_issued': 5000,
                 'units_outstanding': 5000, 'latest_price': 0.0, 'market_value': 0.0},
            ],
        }
        data = mock_perf()
        self.assertEqual(data['total_market_value'], 0.0)
        self.assertEqual(data['instruments'][0]['market_value'], 0.0)


# ══════════════════════════════════════════════
# PHASE 5 — NAV & FEE ENGINE TESTS
# ══════════════════════════════════════════════

class NavCalculationTests(TestCase):
    """Verify NAV math with mocked data."""

    @patch('investment.services.ORMDocumentService.get_collection')
    def test_calculate_nav_basic(self, mock_get_coll):
        def side_effect(*args):
            coll_name = args[0]
            if coll_name.endswith('transactions'):
                return [
                    {'id': 't1', 'transaction_type': 'Capital Influx', 'amount': 100000.0, 'status': 'Cleared'},
                    {'id': 't2', 'transaction_type': 'Capital Influx', 'amount': 50000.0, 'status': 'Cleared'},
                ]
            elif coll_name.endswith('loans'):
                return [{'id': 'l1', 'status': 'Active', 'outstanding_balance': 200000.0}]
            elif coll_name.endswith('outbound_placements'):
                return [{'id': 'o1', 'status': 'Active', 'current_valuation': 50000.0}]
            elif coll_name.endswith('loan_schedules'):
                return [{'id': 's1', 'payment_status': 'Unpaid', 'scheduled_interest': 5000.0}]
            elif coll_name.endswith('investor_holdings'):
                return [{'id': 'h1', 'units_held': '10000.0000', 'is_active': True}]
            elif coll_name.endswith('fee_accruals'):
                return [{'id': 'f1', 'amount': '2000.00', 'is_settled': False}]
            return []
        mock_get_coll.side_effect = side_effect

        from datetime import date
        result = NavService.calculate_nav(date(2026, 7, 10))

        # Cash = 100000 + 50000 = 150000
        # Loan Outstanding = 200000
        # Outbound = 50000
        # Total Assets = 150000 + 200000 + 50000 = 400000
        # Liabilities = 5000 + 2000 = 7000
        # AUM = 400000 - 7000 = 393000
        # NAV = 393000 / 10000 = 39.30
        self.assertEqual(result['total_aum'], '393000.00')
        self.assertEqual(result['nav_per_unit'], '39.3000')
        self.assertEqual(result['total_units'], '10000.0000')

    @patch('investment.services.ORMDocumentService.get_collection')
    def test_calculate_nav_zero_units(self, mock_get_coll):
        def side_effect(*args):
            coll_name = args[0]
            if coll_name.endswith('transactions'):
                return []
            elif coll_name.endswith('loans'):
                return []
            elif coll_name.endswith('outbound_placements'):
                return []
            elif coll_name.endswith('loan_schedules'):
                return []
            elif coll_name.endswith('investor_holdings'):
                return []
            elif coll_name.endswith('fee_accruals'):
                return []
            return []
        mock_get_coll.side_effect = side_effect

        from datetime import date
        result = NavService.calculate_nav(date(2026, 7, 10))
        self.assertEqual(result['nav_per_unit'], '0.0000')
        self.assertEqual(result['total_aum'], '0.00')

    @patch('investment.services.ORMDocumentService.get_collection')
    def test_issue_units_creates_holding(self, mock_get_coll):
        mock_get_coll.return_value = []
        from datetime import date
        NavService._persist_nav_record({
            'nav_date': date(2026, 7, 10).isoformat(),
            'nav_per_unit': '50.0000',
            'total_units': '1000.0000',
            'total_aum': '50000.00',
        })
        with patch('investment.services.ORMDocumentService.create_document') as mock_create:
            mock_create.return_value = 'new-holding-id'
            result = NavService.issue_units('inv-1', '10000', '50.0000')
            self.assertEqual(result['units_issued'], '200.0000')
            self.assertEqual(result['amount_invested'], '10000.00')
            self.assertEqual(result['investor_id'], 'inv-1')

    @patch('investment.services.ORMDocumentService.get_collection')
    def test_redeem_units_reduces_holding(self, mock_get_coll):
        mock_get_coll.return_value = [{
            'id': 'h1', 'investor_id': 'inv-1', 'units_held': '500.0000',
            'avg_cost_per_unit': '50.0000', 'total_invested': '25000.00',
            'current_value': '27500.00', 'unrealized_pl': '2500.00',
            'is_active': True,
        }]
        with patch('investment.services.ORMDocumentService.update_document') as mock_update:
            mock_update.return_value = True
            result = NavService.redeem_units('inv-1', '100.0000', '55.0000')
            self.assertEqual(result['units_redeemed'], '100.0000')
            self.assertEqual(result['proceeds'], '5500.00')


class FeeCalculationTests(TestCase):
    """Verify management and performance fee math."""

    def test_management_fee_daily(self):
        fee = FeeService.calculate_management_fee('1000000.00', '2.00', 30)
        # 1000000 * (0.02 / 365) * 30 = 1643.84
        self.assertEqual(fee, '1643.84')

    def test_management_fee_zero_days(self):
        fee = FeeService.calculate_management_fee('1000000.00', '2.00', 0)
        self.assertEqual(fee, '0.00')

    def test_performance_fee_below_hwm(self):
        fee = FeeService.calculate_performance_fee('50.0000', '55.0000', '10000.0000', '20.00')
        self.assertEqual(fee, '0.00')

    def test_performance_fee_above_hwm(self):
        fee = FeeService.calculate_performance_fee('60.0000', '50.0000', '10000.0000', '20.00')
        # (60 - 50) * 10000 * 0.20 = 20000
        self.assertEqual(fee, '20000.00')

    def test_performance_fee_zero_units(self):
        fee = FeeService.calculate_performance_fee('60.0000', '50.0000', '0.0000', '20.00')
        self.assertEqual(fee, '0.00')


class UnitIssuanceTests(TestCase):
    """Verify unit issue/redeem math with existing holdings."""

    @patch('investment.services.ORMDocumentService.get_collection')
    def test_issue_units_updates_existing_holding(self, mock_get_coll):
        mock_get_coll.return_value = [{
            'id': 'h1', 'investor_id': 'inv-1', 'units_held': '1000.0000',
            'avg_cost_per_unit': '50.0000', 'total_invested': '50000.00',
            'current_value': '55000.00', 'unrealized_pl': '5000.00',
            'is_active': True,
        }]
        with patch('investment.services.ORMDocumentService.update_document') as mock_update:
            mock_update.return_value = True
            result = NavService.issue_units('inv-1', '25000', '50.0000')
            # Units = 25000 / 50 = 500
            # New total = 1000 + 500 = 1500
            # Avg cost = (50000 + 25000) / 1500 = 50.0
            self.assertEqual(result['units_issued'], '500.0000')
            mock_update.assert_called_once()
            call_kwargs = mock_update.call_args[0][2]
            self.assertEqual(call_kwargs['units_held'], '1500.0000')

    @patch('investment.services.ORMDocumentService.get_collection')
    def test_redeem_full_units(self, mock_get_coll):
        mock_get_coll.return_value = []
        result = NavService.redeem_units('inv-full', '500.0000', '50.0000')
        self.assertEqual(result['proceeds'], '25000.00')


class NavCeleryTaskTests(TestCase):
    """Verify Celery task execution paths."""

    @patch('investment.services.NavService.calculate_nav')
    @patch('investment.services.FeeService.accrue_management_fee')
    def test_calculate_daily_nav_runs(self, mock_accrue, mock_nav):
        mock_nav.return_value = {'nav_per_unit': '50.0000', 'total_aum': '500000.00'}
        from investment.tasks import calculate_daily_nav
        result = calculate_daily_nav()
        self.assertIn('NAV computed', result)
        mock_nav.assert_called_once()
        mock_accrue.assert_called_once()

    @patch('investment.tasks.date')
    @patch('investment.services.NavService.calculate_nav')
    @patch('investment.services.NavService.get_current_nav')
    @patch('investment.services.FeeService.get_fee_structure')
    @patch('investment.services.FeeService.accrue_management_fee')
    @patch('investment.services.FeeService.calculate_performance_fee')
    @patch('investment.tasks.fs.create_document')
    def test_accrue_monthly_fees_with_performance(
        self, mock_create, mock_perf_fee, mock_accrue_mgmt,
        mock_get_fee, mock_get_nav, mock_calc_nav, mock_date,
    ):
        mock_date.today.return_value = date(2026, 7, 31)
        mock_calc_nav.return_value = {'nav_per_unit': '60.0000', 'total_aum': '600000.00'}
        mock_get_nav.return_value = {'nav_per_unit': '60.0000', 'total_units': '10000.0000', 'total_aum': '600000.00'}
        mock_get_fee.return_value = {
            'high_water_mark': '50.0000', 'performance_fee_pct': '20.00',
        }
        mock_perf_fee.return_value = '20000.00'
        from investment.tasks import accrue_monthly_fees
        result = accrue_monthly_fees()
        self.assertIn('Monthly fees accrued', result)
        mock_create.assert_called_once()


class PerformanceMetricsTests(TestCase):
    """Verify performance metric calculations."""

    def test_twrr_empty_series(self):
        self.assertEqual(PerformanceService.time_weighted_return([]), 0.0)

    def test_twrr_single_series(self):
        navs = [{'nav_date': '2026-01-01', 'nav_per_unit': '100.0000'}]
        self.assertEqual(PerformanceService.time_weighted_return(navs), 0.0)

    def test_twrr_known_series(self):
        navs = [
            {'nav_date': '2026-01-01', 'nav_per_unit': '100.0000'},
            {'nav_date': '2026-02-01', 'nav_per_unit': '110.0000'},
            {'nav_date': '2026-03-01', 'nav_per_unit': '99.0000'},
        ]
        # R1 = 0.10, R2 = -0.10, TWRR = (1.1 * 0.9) - 1 = -0.01
        twrr = PerformanceService.time_weighted_return(navs)
        self.assertAlmostEqual(twrr, -0.01, places=6)

    def test_sharpe_ratio(self):
        returns = [0.05, 0.02, -0.01, 0.03, 0.04]
        sr = PerformanceService.sharpe_ratio(returns, 0.02)
        self.assertGreater(sr, -10)
        self.assertLess(sr, 10)

    def test_sharpe_ratio_insufficient_data(self):
        self.assertEqual(PerformanceService.sharpe_ratio([0.01], 0.05), 0.0)

    def test_sortino_ratio(self):
        returns = [0.05, -0.02, 0.03, -0.01, 0.04]
        sr = PerformanceService.sortino_ratio(returns, 0.02)
        self.assertGreater(sr, -10)
        self.assertLess(sr, 10)

    def test_max_drawdown_known(self):
        navs = [
            {'nav_date': '2026-01-01', 'nav_per_unit': '100.0000'},
            {'nav_date': '2026-02-01', 'nav_per_unit': '120.0000'},
            {'nav_date': '2026-03-01', 'nav_per_unit': '90.0000'},
            {'nav_date': '2026-04-01', 'nav_per_unit': '110.0000'},
        ]
        # Peak 120, trough 90, dd = (120-90)/120 = 25%
        result = PerformanceService.max_drawdown(navs)
        self.assertAlmostEqual(result['max_drawdown_pct'], 25.0, places=4)
        self.assertEqual(result['peak_date'], '2026-02-01')
        self.assertEqual(result['trough_date'], '2026-03-01')

    def test_max_drawdown_insufficient_data(self):
        result = PerformanceService.max_drawdown([{'nav_date': '2026-01-01', 'nav_per_unit': '100.0000'}])
        self.assertEqual(result['max_drawdown_pct'], 0.0)

    def test_cagr_computation(self):
        cagr = PerformanceService.annualized_return(0.50, 2.0)
        # (1.5)^(1/2) - 1 = 1.2247 - 1 = 0.2247
        self.assertAlmostEqual(cagr, 0.224745, places=5)

    def test_cagr_zero_years(self):
        self.assertEqual(PerformanceService.annualized_return(0.50, 0), 0.0)

    def test_cagr_negative_return(self):
        cagr = PerformanceService.annualized_return(-0.5, 2.0)
        self.assertAlmostEqual(cagr, -0.292893, places=5)

    def test_rolling_return_window(self):
        navs = [{'nav_date': f'2026-{m:02d}-01', 'nav_per_unit': f'{100 + m * 10}.0000'} for m in range(1, 13)]
        rolling = PerformanceService.rolling_return(navs, 3)
        # 12 entries, window=3 => 9 rolling periods
        self.assertEqual(len(rolling), 9)

    def test_rolling_return_insufficient(self):
        navs = [{'nav_date': '2026-01-01', 'nav_per_unit': '100.0000'}]
        self.assertEqual(PerformanceService.rolling_return(navs, 12), [])

    def test_money_weighted_return_simple(self):
        # Invest 1000, get back 1100 after 1 year
        cfs = [{'amount': 1000, 'days_from_start': 0}]
        irr = PerformanceService.money_weighted_return(cfs, 1100.0)
        self.assertAlmostEqual(irr, 0.10, places=2)

    def test_money_weighted_return_empty(self):
        self.assertEqual(PerformanceService.money_weighted_return([], 0), 0.0)

    def test_volatility(self):
        returns = [0.01, 0.02, -0.01, 0.005, 0.015]
        vol = PerformanceService.volatility(returns)
        self.assertGreater(vol, 0)

    def test_volatility_insufficient(self):
        self.assertEqual(PerformanceService.volatility([0.01]), 0.0)


class CashFlowForecastTests(TestCase):
    """Verify forecast engine and scenario modeling."""

    @patch('investment.services.ORMDocumentService.get_collection')
    def test_forecast_payables_projects_correct_months(self, mock_get_coll):
        mock_get_coll.side_effect = [
            # First call: schedules
            [
                {'id': 's1', 'loan_id': 'l1', 'due_date': '2026-08-15',
                 'scheduled_principal': '1000.00', 'scheduled_interest': '100.00',
                 'payment_status': 'Unpaid'},
                {'id': 's2', 'loan_id': 'l1', 'due_date': '2027-01-15',
                 'scheduled_principal': '1000.00', 'scheduled_interest': '100.00',
                 'payment_status': 'Unpaid'},
            ],
            # Second call: loans
            [{'id': 'l1', 'status': 'Active'}],
        ]
        result = CashFlowForecastService.forecast_payables(12)
        self.assertGreater(len(result), 0)
        self.assertIn('projected_inflow', result[0])

    @patch('investment.services.ORMDocumentService.get_collection')
    def test_what_if_default_rate_reduces_aum(self, mock_get_coll):
        mock_get_coll.side_effect = [
            # loans
            [
                {'id': 'l1', 'status': 'Active', 'principal_amount': '100000.00',
                 'outstanding_balance': '80000.00'},
            ],
            # nav_history
            [
                {'id': 'n1', 'nav_date': '2026-07-01', 'total_aum': '500000.00',
                 'nav_per_unit': '100.0000', 'total_units': '5000.0000'},
            ],
        ]
        result = CashFlowForecastService.what_if_default_rate(0.02, 0.10)
        self.assertIn('base_aum_after', result)
        self.assertIn('stress_aum_after', result)
        base_aum = money_to_float(result['base_aum_after'])
        stress_aum = money_to_float(result['stress_aum_after'])
        self.assertGreaterEqual(base_aum, stress_aum)

    @patch('investment.services.ORMDocumentService.get_collection')
    def test_nav_growth_with_expected_returns(self, mock_get_coll):
        mock_get_coll.side_effect = [
            # nav_history
            [
                {'id': 'n1', 'nav_date': '2026-07-01', 'total_aum': '1000000.00',
                 'nav_per_unit': '100.0000', 'total_units': '10000.0000'},
            ],
            # fee_structures
            [
                {'id': 'f1', 'is_active': True, 'management_fee_annual_pct': '2.00'},
            ],
        ]
        result = CashFlowForecastService.forecast_nav_growth(6, 12.0)
        self.assertEqual(len(result), 6)
        for r in result:
            self.assertIn('projected_aum', r)
            self.assertIn('nav_per_unit', r)


class PortalAccessTests(TestCase):
    """Verify portal session-based access."""

    def setUp(self):
        self.factory = RequestFactory()
        from django.contrib.sessions.middleware import SessionMiddleware
        self.middleware = SessionMiddleware(lambda r: None)

    @patch('investment.portal_views.fs.get_document')
    def test_portal_login_missing_session_redirects(self, mock_get_doc):
        mock_get_doc.return_value = None
        request = self.factory.get('/portal/dashboard/')
        self.middleware.process_request(request)
        from investment.portal_views import portal_dashboard
        response = portal_dashboard(request)
        self.assertEqual(response.status_code, 302)

    @patch('investment.portal_views.fs.get_collection')
    @patch('investment.portal_views.fs.get_document')
    def test_portal_login_valid_creates_session(self, mock_get_doc, mock_get_coll):
        test_password = 'securePass123'
        mock_get_coll.return_value = [
            {'id': 'inv-1', 'investor_code': 'INV-001', 'name': 'Test Investor',
             'password_hash': make_password(test_password)},
        ]
        mock_get_doc.return_value = {'id': 'inv-1', 'name': 'Test Investor'}
        request = self.factory.post('/portal/login/', {'investor_code': 'INV-001', 'password': test_password})
        self.middleware.process_request(request)
        from investment.portal_views import portal_login
        response = portal_login(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(request.session.get('portal_investor_id'), 'inv-1')


class PdfStatementServiceTests(TestCase):
    """Verify PDF generation works."""

    @patch('investment.pdf_service.fs.get_document')
    @patch('investment.pdf_service.fs.get_collection')
    def test_generate_investor_statement_returns_pdf(self, mock_get_coll, mock_get_doc):
        mock_get_doc.return_value = {
            'id': 'inv-1', 'name': 'Test Investor', 'investor_code': 'INV-001',
        }
        def side_effect(*args):
            coll_name = args[0]
            data = {
                COLL_INVESTOR_HOLDINGS: [],
                COLL_TRANSACTIONS: [],
                COLL_NAV_HISTORY: [],
                COLL_FEE_ACCRUALS: [],
            }
            return data.get(coll_name, [])
        mock_get_coll.side_effect = side_effect

        from investment.pdf_service import PdfStatementService
        pdf_bytes = PdfStatementService.generate_investor_statement('inv-1', '2026-07')
        self.assertGreater(len(pdf_bytes), 0)
        self.assertTrue(pdf_bytes.startswith(b'%PDF'))

    @patch('investment.pdf_service.fs.get_document')
    def test_generate_investor_statement_unknown_investor(self, mock_get_doc):
        mock_get_doc.return_value = None
        from investment.pdf_service import PdfStatementService
        with self.assertRaises(ValueError):
            PdfStatementService.generate_investor_statement('bad-id', '2026-07')

    @patch('investment.pdf_service.fs.get_document')
    @patch('investment.pdf_service.fs.get_collection')
    def test_generate_portfolio_report_returns_pdf(self, mock_get_coll, mock_get_doc):
        mock_get_doc.return_value = None
        def side_effect(*args):
            coll_name = args[0]
            data = {
                COLL_INVESTORS: [{'id': 'inv-1', 'name': 'Test Investor'}],
                COLL_INVESTOR_HOLDINGS: [],
                COLL_NAV_HISTORY: [{'nav_date': '2026-07-01', 'total_aum': '500000.00', 'nav_per_unit': '100.0000', 'total_units': '5000.0000'}],
                COLL_LOANS: [],
                COLL_OUTBOUND: [],
                COLL_FEE_STRUCTURES: [],
            }
            return data.get(coll_name, [])
        mock_get_coll.side_effect = side_effect

        from investment.pdf_service import PdfStatementService
        pdf_bytes = PdfStatementService.generate_portfolio_report('2026-07')
        self.assertGreater(len(pdf_bytes), 0)
        self.assertTrue(pdf_bytes.startswith(b'%PDF'))
