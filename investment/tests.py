import json
from datetime import date
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from investment import models


class InvestorModelTestCase(TestCase):
    def setUp(self):
        self.investor = models.Investor.objects.create(
            investor_code='INV-001', name='John Capital',
        )

    def test_str_returns_code_and_name(self):
        self.assertEqual(str(self.investor), 'INV-001 - John Capital')

    def test_is_active_defaults_true(self):
        self.assertTrue(self.investor.is_active)

    def test_created_at_is_auto_set(self):
        self.assertIsNotNone(self.investor.created_at)


class TransactionModelTestCase(TestCase):
    def setUp(self):
        investor = models.Investor.objects.create(investor_code='INV-001', name='John Capital')
        self.transaction = models.Transaction.objects.create(
            investor=investor, investor_name='John Capital',
            transaction_type='Capital Influx', amount=50000.00,
            value_date=date.today(),
        )

    def test_str_returns_name_type_and_amount(self):
        self.assertIn('John Capital', str(self.transaction))
        self.assertIn('Capital Influx', str(self.transaction))

    def test_is_active_defaults_true(self):
        self.assertTrue(self.transaction.is_active)

    def test_created_at_is_auto_set(self):
        self.assertIsNotNone(self.transaction.created_at)


class LoanModelTestCase(TestCase):
    def setUp(self):
        investor = models.Investor.objects.create(investor_code='INV-001', name='John Capital')
        self.loan = models.Loan.objects.create(
            investor=investor, investor_name='John Capital',
            principal_amount=100000.00, outstanding_balance=100000.00,
            interest_rate=10.00, tenure_months=12,
            disbursement_date=date.today(),
        )

    def test_str_returns_name_amount_and_status(self):
        self.assertIn('John Capital', str(self.loan))
        self.assertIn('Active', str(self.loan))

    def test_is_active_defaults_true(self):
        self.assertTrue(self.loan.is_active)

    def test_created_at_is_auto_set(self):
        self.assertIsNotNone(self.loan.created_at)


class InvestmentAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_investor_list_returns_200(self):
        url = reverse('investment-investor-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_investor_create_returns_201(self):
        url = reverse('investment-investor-list')
        data = {'investor_code': 'INV-100', 'name': 'Jane Capital'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_investor_detail_returns_200(self):
        investor = models.Investor.objects.create(investor_code='INV-002', name='Bob Capital')
        url = reverse('investment-investor-detail', kwargs={'pk': investor.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_investor_update_returns_200(self):
        investor = models.Investor.objects.create(investor_code='INV-003', name='Old Name')
        url = reverse('investment-investor-detail', kwargs={'pk': investor.pk})
        data = {'investor_code': 'INV-003', 'name': 'Updated Name'}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_investor_delete_returns_204(self):
        investor = models.Investor.objects.create(investor_code='INV-004', name='Delete Me')
        url = reverse('investment-investor-detail', kwargs={'pk': investor.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_unauthenticated_access_returns_403(self):
        self.client.force_authenticate(user=None)
        url = reverse('investment-investor-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
