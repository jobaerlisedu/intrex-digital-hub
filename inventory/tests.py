import json
from datetime import date
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from inventory import models
from workflow.models import WorkflowDefinition, WorkflowState, WorkflowInstance


class ProductModelTestCase(TestCase):
    def setUp(self):
        self.product = models.Product.objects.create(item_name='Laptop')

    def test_str_returns_item_name_and_sku(self):
        self.assertIn('Laptop', str(self.product))

    def test_is_active_defaults_true(self):
        self.assertTrue(self.product.is_active)

    def test_created_at_is_auto_set(self):
        self.assertIsNotNone(self.product.created_at)


class VendorModelTestCase(TestCase):
    def setUp(self):
        self.vendor = models.Vendor.objects.create(
            vendor_code='V001', name='Tech Supplies Inc.',
        )

    def test_str_returns_vendor_code_and_name(self):
        self.assertEqual(str(self.vendor), 'V001 - Tech Supplies Inc.')

    def test_is_active_defaults_true(self):
        self.assertTrue(self.vendor.is_active)

    def test_created_at_is_auto_set(self):
        self.assertIsNotNone(self.vendor.created_at)


class RequisitionModelTestCase(TestCase):
    def setUp(self):
        self.requisition = models.Requisition.objects.create(
            requisition_code='REQ001',
        )

    def test_str_returns_code_client_status(self):
        self.assertIn('REQ001', str(self.requisition))

    def test_is_active_defaults_true(self):
        self.assertTrue(self.requisition.is_active)

    def test_created_at_is_auto_set(self):
        self.assertIsNotNone(self.requisition.created_at)


class PurchaseOrderModelTestCase(TestCase):
    def setUp(self):
        self.po = models.PurchaseOrder.objects.create(po_code='PO001')

    def test_str_returns_po_code_and_status(self):
        self.assertEqual(str(self.po), 'PO001 (Draft)')

    def test_is_active_defaults_true(self):
        self.assertTrue(self.po.is_active)

    def test_created_at_is_auto_set(self):
        self.assertIsNotNone(self.po.created_at)


class InventoryAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_product_list_returns_200(self):
        url = reverse('inv-product-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_product_create_returns_201(self):
        url = reverse('inv-product-list')
        data = {'item_name': 'Monitor'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_product_detail_returns_200(self):
        product = models.Product.objects.create(item_name='Keyboard')
        url = reverse('inv-product-detail', kwargs={'pk': product.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_product_update_returns_200(self):
        product = models.Product.objects.create(item_name='Mouse')
        url = reverse('inv-product-detail', kwargs={'pk': product.pk})
        data = {'item_name': 'Wireless Mouse'}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_product_delete_returns_204(self):
        product = models.Product.objects.create(item_name='USB Cable')
        url = reverse('inv-product-detail', kwargs={'pk': product.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_unauthenticated_access_returns_403(self):
        self.client.force_authenticate(user=None)
        url = reverse('inv-product-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class InventoryWorkflowTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin', password='pass')
        self.wf_def = WorkflowDefinition.objects.create(
            name='Requisition Approval', module='inventory', entity_type='requisition',
        )
        self.initial_state = WorkflowState.objects.create(
            workflow=self.wf_def, state_key='pending_approval', label='Pending Approval', is_initial=True,
        )

    def test_workflow_instance_can_be_created_for_requisition(self):
        req = models.Requisition.objects.create(requisition_code='REQ002')
        wf_instance = WorkflowInstance.objects.create(
            workflow=self.wf_def,
            entity_id=str(req.pk),
            entity_label=str(req),
            current_state=self.initial_state,
            started_by=self.user,
        )
        self.assertEqual(wf_instance.workflow.module, 'inventory')
        self.assertEqual(wf_instance.workflow.entity_type, 'requisition')
        self.assertTrue(wf_instance.is_active)

    def test_requisition_status_transition(self):
        req = models.Requisition.objects.create(requisition_code='REQ003', status='Pending Approval')
        req.status = 'Approved'
        req.save()
        self.assertEqual(req.status, 'Approved')
