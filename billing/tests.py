import json
from datetime import date
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from billing import models
from workflow.models import WorkflowDefinition, WorkflowState, WorkflowInstance


class ChartOfAccountModelTestCase(TestCase):
    def setUp(self):
        self.account = models.ChartOfAccount.objects.create(
            account_code='1001', name='Cash', account_type='Asset',
        )

    def test_str_returns_code_and_name(self):
        self.assertEqual(str(self.account), '1001 - Cash')

    def test_is_active_defaults_true(self):
        self.assertTrue(self.account.is_active)

    def test_created_at_is_auto_set(self):
        self.assertIsNotNone(self.account.created_at)


class InvoiceModelTestCase(TestCase):
    def setUp(self):
        self.invoice = models.Invoice.objects.create(
            invoice_number='INV-001', client_name='ABC Corp',
            issue_date=date.today(), due_date=date.today(),
        )

    def test_str_returns_number_client_status(self):
        self.assertEqual(str(self.invoice), 'INV-001 - ABC Corp (Pending)')

    def test_is_active_defaults_true(self):
        self.assertTrue(self.invoice.is_active)

    def test_created_at_is_auto_set(self):
        self.assertIsNotNone(self.invoice.created_at)


class JournalEntryModelTestCase(TestCase):
    def setUp(self):
        self.je = models.JournalEntry.objects.create(
            entry_code='JE-001', posting_date=date.today(),
        )

    def test_str_returns_entry_code_and_status(self):
        self.assertEqual(str(self.je), 'JE-001 (Draft)')

    def test_is_active_defaults_true(self):
        self.assertTrue(self.je.is_active)

    def test_created_at_is_auto_set(self):
        self.assertIsNotNone(self.je.created_at)


class PaymentModelTestCase(TestCase):
    def setUp(self):
        self.payment = models.Payment.objects.create(
            receipt_code='RCT-001', payment_date=date.today(), amount=1000.00,
        )

    def test_str_returns_receipt_code_and_amount(self):
        self.assertIn('RCT-001', str(self.payment))
        self.assertIn('1000', str(self.payment))

    def test_is_active_defaults_true(self):
        self.assertTrue(self.payment.is_active)

    def test_created_at_is_auto_set(self):
        self.assertIsNotNone(self.payment.created_at)


class BillingAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_chart_of_account_list_returns_200(self):
        url = reverse('billing-chart-of-account-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invoice_create_returns_201(self):
        url = reverse('billing-invoice-list')
        data = {
            'invoice_number': 'INV-100',
            'client_name': 'XYZ Ltd',
            'issue_date': str(date.today()),
            'due_date': str(date.today()),
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_invoice_detail_returns_200(self):
        inv = models.Invoice.objects.create(
            invoice_number='INV-101', client_name='Client A',
            issue_date=date.today(), due_date=date.today(),
        )
        url = reverse('billing-invoice-detail', kwargs={'pk': inv.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invoice_update_returns_200(self):
        inv = models.Invoice.objects.create(
            invoice_number='INV-102', client_name='Client B',
            issue_date=date.today(), due_date=date.today(),
        )
        url = reverse('billing-invoice-detail', kwargs={'pk': inv.pk})
        data = {
            'invoice_number': 'INV-102',
            'client_name': 'Client B Updated',
            'issue_date': str(date.today()),
            'due_date': str(date.today()),
            'status': 'Paid',
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invoice_delete_returns_204(self):
        inv = models.Invoice.objects.create(
            invoice_number='INV-103', client_name='Client C',
            issue_date=date.today(), due_date=date.today(),
        )
        url = reverse('billing-invoice-detail', kwargs={'pk': inv.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_unauthenticated_access_returns_403(self):
        self.client.force_authenticate(user=None)
        url = reverse('billing-chart-of-account-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class BillingWorkflowTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin', password='pass')
        self.wf_def = WorkflowDefinition.objects.create(
            name='Invoice Approval', module='billing', entity_type='invoice',
        )
        self.initial_state = WorkflowState.objects.create(
            workflow=self.wf_def, state_key='pending', label='Pending', is_initial=True,
        )

    def test_workflow_instance_can_be_created_for_invoice(self):
        inv = models.Invoice.objects.create(
            invoice_number='INV-WF1', client_name='WF Client',
            issue_date=date.today(), due_date=date.today(),
        )
        wf_instance = WorkflowInstance.objects.create(
            workflow=self.wf_def,
            entity_id=str(inv.pk),
            entity_label=str(inv),
            current_state=self.initial_state,
            started_by=self.user,
        )
        self.assertEqual(wf_instance.workflow.module, 'billing')
        self.assertEqual(wf_instance.workflow.entity_type, 'invoice')
        self.assertTrue(wf_instance.is_active)

    def test_invoice_status_transition(self):
        inv = models.Invoice.objects.create(
            invoice_number='INV-WF2', client_name='WF Client 2',
            issue_date=date.today(), due_date=date.today(), status='Pending',
        )
        inv.status = 'Paid'
        inv.save()
        self.assertEqual(inv.status, 'Paid')
