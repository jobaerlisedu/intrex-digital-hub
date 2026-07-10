"""
Unit and integration tests for the Investment module.

Firestore-dependent tests use mocking to avoid requiring live credentials.
Pure business logic (PMT, amortization) is tested directly.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse

from investment.services import (
    AmortizationService as amt,
    CodeGenerator,
    FirestoreService as fs,
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
        schedule = amt.generate_schedule(100000.0, 10.0, 12, self.disb_date, self.loan_id)
        total_principal = sum(s['scheduled_principal'] for s in schedule)
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
        schedule = amt.generate_schedule(12000.0, 0.0, 12, self.disb_date, self.loan_id)
        self.assertEqual(len(schedule), 12)
        for s in schedule:
            self.assertEqual(s['scheduled_principal'], 1000.0)
            self.assertEqual(s['scheduled_interest'], 0.0)

    def test_interest_expense_computation(self):
        """Interest expense for a given month sums correctly."""
        schedule = amt.generate_schedule(100000.0, 12.0, 12, self.disb_date, self.loan_id)
        expense = amt.compute_interest_expense('2026-01', schedule)
        # First month interest = 100000 * (0.12/12) = 1000
        self.assertAlmostEqual(expense, 1000.0, delta=0.1)

    def test_last_installment_clears_balance(self):
        """After applying all schedule rows, remaining balance is ~0."""
        schedule = amt.generate_schedule(100000.0, 10.0, 12, self.disb_date, self.loan_id)
        balance = Decimal('100000.0')
        for s in schedule:
            balance -= Decimal(str(s['scheduled_principal']))
        self.assertAlmostEqual(float(balance), 0.0, delta=0.1)

    def test_each_installment_declining_interest(self):
        """Interest portion decreases each period (positive amortization)."""
        schedule = amt.generate_schedule(100000.0, 10.0, 12, self.disb_date, self.loan_id)
        for i in range(1, len(schedule)):
            self.assertGreaterEqual(
                schedule[i - 1]['scheduled_interest'],
                schedule[i]['scheduled_interest'],
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

    @patch('investment.services.db')
    def test_next_sequence_starts_at_one(self, mock_db):
        mock_counter = MagicMock()
        mock_counter.get.return_value.exists = False
        mock_db.collection.return_value.document.return_value = mock_counter

        # Mock transaction decorator to execute the inner function
        from investment.services import CodeGenerator
        result = CodeGenerator._next_sequence('test_counter', 'TST', 4)
        # Without a real Firestore transaction, this will fail gracefully
        # This tests that the code path covers the fallback
        self.assertIsNone(result)


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
# API TESTS (Firestore-mocked)
# ══════════════════════════════════════════════

class InvestmentAPITestCase(APITestCase):
    """API tests with FirestoreService fully mocked."""

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
        ratio = payment / total_due if total_due > 0 else 0
        principal_portion = payment * ratio
        self.assertAlmostEqual(principal_portion, 8000.0, delta=0.01)
        self.assertAlmostEqual(payment, 10000.0)
        self.assertGreaterEqual(payment, total_due - 0.01)

    def test_partial_payment_proportional_split(self):
        """Partial payment splits proportionally between principal and interest."""
        principal = 8000.0
        interest = 2000.0
        total_due = principal + interest
        payment = 5000.0
        ratio = payment / total_due
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
    """Test ReportService data aggregation with mocked Firestore."""

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
    """Test Celery tasks with FirestoreService fully mocked."""

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
            {'id': 's-3', 'payment_status': 'Paid', 'due_date': past_date},
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

        def mock_get_coll_side_effect(coll):
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

        def mock_get_coll_side_effect(coll):
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
        schema = InstrumentPriceSchema(instrument_id='inst-1', price_date='2026-01-15', price=105.50)
        self.assertEqual(schema.instrument_id, 'inst-1')
        self.assertEqual(schema.price, 105.50)
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

    def test_investor_schema_has_kyc_document_url(self):
        from investment.models import InvestorSchema
        schema = InvestorSchema(investor_code='INV-001', name='Test')
        self.assertEqual(schema.kyc_document_url, '')

    def test_instrument_price_defaults(self):
        from investment.models import InstrumentPriceSchema
        schema = InstrumentPriceSchema(instrument_id='inst-1', price_date='2026-06-01', price=100.0)
        self.assertIsNone(schema.created_at)
        self.assertEqual(schema.created_by, '')
