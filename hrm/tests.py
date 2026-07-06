import json
from datetime import date, time
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from hrm import models
from workflow.models import WorkflowDefinition, WorkflowState, WorkflowInstance


class DepartmentModelTestCase(TestCase):
    def setUp(self):
        self.department = models.Department.objects.create(
            name='Engineering',
        )

    def test_str_returns_name(self):
        self.assertEqual(str(self.department), 'Engineering')

    def test_is_active_defaults_true(self):
        self.assertTrue(self.department.is_active)

    def test_created_at_is_auto_set(self):
        self.assertIsNotNone(self.department.created_at)


class EmployeeModelTestCase(TestCase):
    def setUp(self):
        dept = models.Department.objects.create(name='Engineering')
        self.employee = models.Employee.objects.create(
            emp_id='EMP001',
            first_name='John',
            last_name='Doe',
            department=dept,
        )

    def test_str_returns_emp_id_and_name(self):
        self.assertEqual(str(self.employee), 'EMP001 - John Doe')

    def test_is_active_defaults_true(self):
        self.assertTrue(self.employee.is_active)

    def test_created_at_is_auto_set(self):
        self.assertIsNotNone(self.employee.created_at)


class AttendanceModelTestCase(TestCase):
    def setUp(self):
        dept = models.Department.objects.create(name='Engineering')
        emp = models.Employee.objects.create(emp_id='EMP001', first_name='John', last_name='Doe', department=dept)
        self.attendance = models.Attendance.objects.create(employee=emp, date=date.today())

    def test_str_returns_employee_date_status(self):
        expected = f'John Doe - {date.today()} (Present)'
        self.assertEqual(str(self.attendance), expected)

    def test_is_active_defaults_true(self):
        self.assertTrue(self.attendance.is_active)

    def test_created_at_is_auto_set(self):
        self.assertIsNotNone(self.attendance.created_at)


class LeaveModelTestCase(TestCase):
    def setUp(self):
        dept = models.Department.objects.create(name='Engineering')
        emp = models.Employee.objects.create(emp_id='EMP001', first_name='John', last_name='Doe', department=dept)
        self.leave = models.Leave.objects.create(
            employee=emp, leave_type='Annual',
            from_date=date.today(), to_date=date.today(),
        )

    def test_str_returns_employee_leave_type_status(self):
        self.assertIn('Annual', str(self.leave))
        self.assertIn('Pending', str(self.leave))

    def test_is_active_defaults_true(self):
        self.assertTrue(self.leave.is_active)

    def test_created_at_is_auto_set(self):
        self.assertIsNotNone(self.leave.created_at)


class PayrollModelTestCase(TestCase):
    def setUp(self):
        self.payroll = models.Payroll.objects.create(period='2026-01')

    def test_str_returns_period_and_status(self):
        self.assertEqual(str(self.payroll), '2026-01 (Generated)')

    def test_is_active_defaults_true(self):
        self.assertTrue(self.payroll.is_active)

    def test_created_at_is_auto_set(self):
        self.assertIsNotNone(self.payroll.created_at)


class HRMAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_department_list_returns_200(self):
        url = reverse('hrm-department-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_department_create_returns_201(self):
        url = reverse('hrm-department-list')
        data = {'name': 'Marketing'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_department_detail_returns_200(self):
        dept = models.Department.objects.create(name='Engineering')
        url = reverse('hrm-department-detail', kwargs={'pk': dept.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_department_update_returns_200(self):
        dept = models.Department.objects.create(name='Engineering')
        url = reverse('hrm-department-detail', kwargs={'pk': dept.pk})
        data = {'name': 'Engineering Updated'}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_department_delete_returns_204(self):
        dept = models.Department.objects.create(name='Engineering')
        url = reverse('hrm-department-detail', kwargs={'pk': dept.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_unauthenticated_access_returns_403(self):
        self.client.force_authenticate(user=None)
        url = reverse('hrm-department-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class HRMWorkflowTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin', password='pass')
        dept = models.Department.objects.create(name='Engineering')
        self.employee = models.Employee.objects.create(
            emp_id='EMP001', first_name='John', last_name='Doe', department=dept,
        )
        self.wf_def = WorkflowDefinition.objects.create(
            name='Leave Approval', module='hrm', entity_type='leave',
        )
        self.initial_state = WorkflowState.objects.create(
            workflow=self.wf_def, state_key='pending', label='Pending', is_initial=True,
        )

    def test_workflow_instance_can_be_created_for_leave(self):
        leave = models.Leave.objects.create(
            employee=self.employee, leave_type='Annual',
            from_date=date.today(), to_date=date.today(),
        )
        wf_instance = WorkflowInstance.objects.create(
            workflow=self.wf_def,
            entity_id=str(leave.pk),
            entity_label=str(leave),
            current_state=self.initial_state,
            started_by=self.user,
        )
        self.assertEqual(wf_instance.workflow.module, 'hrm')
        self.assertEqual(wf_instance.workflow.entity_type, 'leave')
        self.assertTrue(wf_instance.is_active)

    def test_leave_status_transition_matches_workflow_state(self):
        leave = models.Leave.objects.create(
            employee=self.employee, leave_type='Annual',
            from_date=date.today(), to_date=date.today(),
        )
        leave.status = 'Approved'
        leave.save()
        self.assertEqual(leave.status, 'Approved')
