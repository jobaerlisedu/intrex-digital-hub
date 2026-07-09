import json
from datetime import date, time
from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from hrm import models
from hrm.services.discipline import DisciplineService
from hrm.validators import (
    validate_disciplinary_data, validate_hearing_data,
    validate_action_data, validate_appeal_data,
)
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


@override_settings(SECURE_SSL_REDIRECT=False)
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

    def test_unauthenticated_access_returns_401(self):
        self.client.force_authenticate(user=None)
        url = reverse('hrm-department-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


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


# ── Disciplinary Cases ─────────────────────────────────────────────────

class DisciplinaryCaseModelTestCase(TestCase):
    def setUp(self):
        dept = models.Department.objects.create(name='Engineering')
        self.employee = models.Employee.objects.create(
            emp_id='EMP010', first_name='Jane', last_name='Smith', department=dept,
        )
        self.case = models.DisciplinaryCase.objects.create(
            employee=self.employee,
            incident_date=date.today(),
            nature_of_offense='Repeated lateness',
        )

    def test_str_returns_case_number_and_employee(self):
        self.assertIn(self.employee.name, str(self.case))
        self.assertIn(self.case.case_number, str(self.case))

    def test_case_number_auto_generated(self):
        self.assertTrue(self.case.case_number.startswith('DC-'))

    def test_severity_defaults_minor(self):
        self.assertEqual(self.case.severity, 'Minor')

    def test_status_defaults_open(self):
        self.assertEqual(self.case.status, 'Open')

    def test_is_active_defaults_true(self):
        self.assertTrue(self.case.is_active)

    def test_created_at_is_auto_set(self):
        self.assertIsNotNone(self.case.created_at)


class DisciplinaryHearingModelTestCase(TestCase):
    def setUp(self):
        from django.utils import timezone
        dept = models.Department.objects.create(name='Engineering')
        emp = models.Employee.objects.create(emp_id='EMP011', first_name='John', last_name='Doe', department=dept)
        case = models.DisciplinaryCase.objects.create(employee=emp, incident_date=date.today(), nature_of_offense='Test')
        self.hearing = models.DisciplinaryHearing.objects.create(
            case=case,
            hearing_date=timezone.now(),
        )

    def test_str_returns_case_number_and_date(self):
        self.assertIn(self.hearing.case.case_number, str(self.hearing))

    def test_status_defaults_scheduled(self):
        self.assertEqual(self.hearing.status, 'Scheduled')

    def test_is_active_defaults_true(self):
        self.assertTrue(self.hearing.is_active)

    def test_created_at_is_auto_set(self):
        self.assertIsNotNone(self.hearing.created_at)


class DisciplinaryActionModelTestCase(TestCase):
    def setUp(self):
        dept = models.Department.objects.create(name='Engineering')
        emp = models.Employee.objects.create(emp_id='EMP012', first_name='Bob', last_name='Brown', department=dept)
        case = models.DisciplinaryCase.objects.create(employee=emp, incident_date=date.today(), nature_of_offense='Test')
        self.action = models.DisciplinaryAction.objects.create(
            case=case,
            action_type='Written Warning',
            description='First written warning',
            issued_date=date.today(),
            effective_date=date.today(),
        )

    def test_str_returns_action_type_and_case_number(self):
        self.assertIn('Written Warning', str(self.action))
        self.assertIn(self.action.case.case_number, str(self.action))

    def test_status_defaults_pending(self):
        self.assertEqual(self.action.status, 'Pending')

    def test_is_active_defaults_true(self):
        self.assertTrue(self.action.is_active)

    def test_created_at_is_auto_set(self):
        self.assertIsNotNone(self.action.created_at)


class DisciplinaryAppealModelTestCase(TestCase):
    def setUp(self):
        dept = models.Department.objects.create(name='Engineering')
        emp = models.Employee.objects.create(emp_id='EMP013', first_name='Alice', last_name='Green', department=dept)
        case = models.DisciplinaryCase.objects.create(employee=emp, incident_date=date.today(), nature_of_offense='Test')
        action = models.DisciplinaryAction.objects.create(
            case=case, action_type='Termination', description='Termination',
            issued_date=date.today(), effective_date=date.today(),
        )
        self.appeal = models.DisciplinaryAppeal.objects.create(
            action=action,
            appeal_date=date.today(),
            grounds='Unfair dismissal',
        )

    def test_str_returns_action_and_date(self):
        self.assertIn(str(self.appeal.action.case.case_number), str(self.appeal))

    def test_status_defaults_submitted(self):
        self.assertEqual(self.appeal.status, 'Submitted')

    def test_is_active_defaults_true(self):
        self.assertTrue(self.appeal.is_active)

    def test_created_at_is_auto_set(self):
        self.assertIsNotNone(self.appeal.created_at)


# ── Disciplinary Validators ─────────────────────────────────────────────

class DisciplinaryValidatorTestCase(TestCase):
    def test_validate_disciplinary_data_passes_with_valid_data(self):
        errors = validate_disciplinary_data({
            'employee': 'some-emp-id',
            'incident_date': '2026-07-10',
            'nature_of_offense': 'Repeated lateness',
            'severity': 'Major',
        })
        self.assertEqual(errors, [])

    def test_validate_disciplinary_data_fails_when_employee_missing(self):
        errors = validate_disciplinary_data({
            'employee': '',
            'incident_date': '2026-07-10',
            'nature_of_offense': 'Lateness',
        })
        self.assertIn('Employee is required', errors)

    def test_validate_disciplinary_data_fails_when_incident_date_missing(self):
        errors = validate_disciplinary_data({
            'employee': 'emp-1',
            'incident_date': '',
            'nature_of_offense': 'Lateness',
        })
        self.assertIn('Incident date is required', errors)

    def test_validate_disciplinary_data_fails_when_offense_missing(self):
        errors = validate_disciplinary_data({
            'employee': 'emp-1',
            'incident_date': '2026-07-10',
            'nature_of_offense': '',
        })
        self.assertIn('Nature of offense is required', errors)

    def test_validate_disciplinary_data_fails_with_invalid_severity(self):
        errors = validate_disciplinary_data({
            'employee': 'emp-1',
            'incident_date': '2026-07-10',
            'nature_of_offense': 'Lateness',
            'severity': 'Extra Severe',
        })
        self.assertIn('Invalid severity level', errors)

    def test_validate_disciplinary_data_fails_with_invalid_date_format(self):
        errors = validate_disciplinary_data({
            'employee': 'emp-1',
            'incident_date': 'not-a-date',
            'nature_of_offense': 'Lateness',
        })
        self.assertIn('Invalid incident date format (use YYYY-MM-DD)', errors)

    def test_validate_hearing_data_passes_with_valid_data(self):
        errors = validate_hearing_data({
            'case_id': 'case-1',
            'hearing_date': '2026-07-15T10:00',
        })
        self.assertEqual(errors, [])

    def test_validate_hearing_data_fails_when_case_missing(self):
        errors = validate_hearing_data({
            'case_id': '',
            'hearing_date': '2026-07-15T10:00',
        })
        self.assertIn('Case is required', errors)

    def test_validate_hearing_data_fails_when_date_missing(self):
        errors = validate_hearing_data({
            'case_id': 'case-1',
            'hearing_date': '',
        })
        self.assertIn('Hearing date is required', errors)

    def test_validate_action_data_passes_with_valid_data(self):
        errors = validate_action_data({
            'case_id': 'case-1',
            'action_type': 'Written Warning',
            'issued_date': '2026-07-10',
            'effective_date': '2026-07-11',
        })
        self.assertEqual(errors, [])

    def test_validate_action_data_fails_when_case_missing(self):
        errors = validate_action_data({'case_id': '', 'action_type': 'Warning', 'issued_date': '2026-07-10', 'effective_date': '2026-07-11'})
        self.assertIn('Case is required', errors)

    def test_validate_action_data_fails_when_action_type_missing(self):
        errors = validate_action_data({'case_id': 'case-1', 'action_type': '', 'issued_date': '2026-07-10', 'effective_date': '2026-07-11'})
        self.assertIn('Action type is required', errors)

    def test_validate_action_data_fails_when_issued_date_missing(self):
        errors = validate_action_data({'case_id': 'case-1', 'action_type': 'Warning', 'issued_date': '', 'effective_date': '2026-07-11'})
        self.assertIn('Issued date is required', errors)

    def test_validate_action_data_fails_when_effective_date_missing(self):
        errors = validate_action_data({'case_id': 'case-1', 'action_type': 'Warning', 'issued_date': '2026-07-10', 'effective_date': ''})
        self.assertIn('Effective date is required', errors)

    def test_validate_appeal_data_passes_with_valid_data(self):
        errors = validate_appeal_data({
            'action_id': 'action-1',
            'appeal_date': '2026-07-20',
            'grounds': 'Unfair decision',
        })
        self.assertEqual(errors, [])

    def test_validate_appeal_data_fails_when_action_missing(self):
        errors = validate_appeal_data({'action_id': '', 'appeal_date': '2026-07-20', 'grounds': 'Unfair'})
        self.assertIn('Action is required', errors)

    def test_validate_appeal_data_fails_when_appeal_date_missing(self):
        errors = validate_appeal_data({'action_id': 'action-1', 'appeal_date': '', 'grounds': 'Unfair'})
        self.assertIn('Appeal date is required', errors)

    def test_validate_appeal_data_fails_when_grounds_missing(self):
        errors = validate_appeal_data({'action_id': 'action-1', 'appeal_date': '2026-07-20', 'grounds': ''})
        self.assertIn('Grounds for appeal are required', errors)


# ── DisciplineService ───────────────────────────────────────────────────

class DisciplineServiceTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='disco_admin', password='pass')
        dept = models.Department.objects.create(name='Engineering')
        self.employee = models.Employee.objects.create(
            emp_id='EMP020', first_name='Service', last_name='Test', department=dept,
        )

    def test_add_case_creates_case_with_generated_number(self):
        result = DisciplineService.add_case({
            'employee': str(self.employee.id),
            'incident_date': '2026-07-10',
            'nature_of_offense': 'Testing service layer',
            'severity': 'Gross',
        }, self.user)
        self.assertEqual(result, 'created')
        case = models.DisciplinaryCase.objects.filter(employee=self.employee).first()
        self.assertIsNotNone(case)
        self.assertTrue(case.case_number.startswith('DC-'))
        self.assertEqual(case.severity, 'Gross')
        self.assertEqual(case.reported_by, self.user)

    def test_add_case_updates_existing_case(self):
        case = models.DisciplinaryCase.objects.create(
            employee=self.employee, incident_date=date.today(), nature_of_offense='Original',
        )
        result = DisciplineService.add_case({
            'doc_id': str(case.id),
            'employee': str(self.employee.id),
            'incident_date': '2026-07-11',
            'nature_of_offense': 'Updated offense',
            'severity': 'Major',
        }, self.user)
        self.assertEqual(result, 'updated')
        case.refresh_from_db()
        self.assertEqual(case.nature_of_offense, 'Updated offense')
        self.assertEqual(case.severity, 'Major')

    def test_add_hearing_creates_hearing_and_updates_case_status(self):
        case = models.DisciplinaryCase.objects.create(
            employee=self.employee, incident_date=date.today(), nature_of_offense='Test',
        )
        result = DisciplineService.add_hearing({
            'case_id': str(case.id),
            'hearing_date': '2026-07-15T10:00:00',
            'panel_members': 'Alice, Bob',
            'location': 'Room 2A',
        }, self.user)
        self.assertEqual(result, 'created')
        self.assertTrue(models.DisciplinaryHearing.objects.filter(case=case).exists())
        case.refresh_from_db()
        self.assertEqual(case.status, 'Hearing Scheduled')

    def test_add_hearing_updates_existing_hearing(self):
        case = models.DisciplinaryCase.objects.create(
            employee=self.employee, incident_date=date.today(), nature_of_offense='Test',
        )
        hearing = models.DisciplinaryHearing.objects.create(case=case, hearing_date=date.today())
        result = DisciplineService.add_hearing({
            'doc_id': str(hearing.id),
            'case_id': str(case.id),
            'hearing_date': '2026-07-16T14:00:00',
            'status': 'Completed',
            'outcome': 'Proceed with action',
        }, self.user)
        self.assertEqual(result, 'updated')
        hearing.refresh_from_db()
        self.assertEqual(hearing.status, 'Completed')
        self.assertEqual(hearing.outcome, 'Proceed with action')

    def test_add_hearing_returns_none_without_case_id(self):
        result = DisciplineService.add_hearing({'hearing_date': '2026-07-15T10:00:00'}, self.user)
        self.assertIsNone(result)

    def test_add_action_creates_action(self):
        case = models.DisciplinaryCase.objects.create(
            employee=self.employee, incident_date=date.today(), nature_of_offense='Test',
        )
        result = DisciplineService.add_action({
            'case_id': str(case.id),
            'action_type': 'Suspension',
            'description': '3-day suspension',
            'issued_date': '2026-07-10',
            'effective_date': '2026-07-11',
            'expiry_date': '2026-07-13',
        }, self.user)
        self.assertEqual(result, 'created')
        action = models.DisciplinaryAction.objects.filter(case=case).first()
        self.assertIsNotNone(action)
        self.assertEqual(action.action_type, 'Suspension')
        self.assertEqual(action.issued_by, self.user)

    def test_add_action_updates_existing_action(self):
        case = models.DisciplinaryCase.objects.create(
            employee=self.employee, incident_date=date.today(), nature_of_offense='Test',
        )
        action = models.DisciplinaryAction.objects.create(
            case=case, action_type='Verbal Warning', description='Test',
            issued_date=date.today(), effective_date=date.today(),
        )
        result = DisciplineService.add_action({
            'doc_id': str(action.id),
            'case_id': str(case.id),
            'action_type': 'Written Warning',
            'description': 'Upgraded to written',
            'issued_date': '2026-07-10',
            'effective_date': '2026-07-11',
        }, self.user)
        self.assertEqual(result, 'updated')
        action.refresh_from_db()
        self.assertEqual(action.action_type, 'Written Warning')

    def test_add_action_returns_none_without_case_id(self):
        result = DisciplineService.add_action({
            'action_type': 'Warning', 'description': 'Test',
            'issued_date': '2026-07-10', 'effective_date': '2026-07-11',
        }, self.user)
        self.assertIsNone(result)

    def test_add_appeal_creates_appeal_and_updates_action_status(self):
        case = models.DisciplinaryCase.objects.create(
            employee=self.employee, incident_date=date.today(), nature_of_offense='Test',
        )
        action = models.DisciplinaryAction.objects.create(
            case=case, action_type='Termination', description='Terminated',
            issued_date=date.today(), effective_date=date.today(),
        )
        result = DisciplineService.add_appeal({
            'action_id': str(action.id),
            'appeal_date': '2026-07-20',
            'grounds': 'Unfair termination',
            'supporting_evidence': 'Email chain attached',
        }, self.user)
        self.assertEqual(result, 'created')
        self.assertTrue(models.DisciplinaryAppeal.objects.filter(action=action).exists())
        action.refresh_from_db()
        self.assertEqual(action.status, 'Under Appeal')

    def test_add_appeal_returns_none_without_action_id(self):
        result = DisciplineService.add_appeal({
            'appeal_date': '2026-07-20', 'grounds': 'Unfair',
        }, self.user)
        self.assertIsNone(result)

    def test_resolve_appeal_upheld_enforces_action(self):
        case = models.DisciplinaryCase.objects.create(
            employee=self.employee, incident_date=date.today(), nature_of_offense='Test',
        )
        action = models.DisciplinaryAction.objects.create(
            case=case, action_type='Suspension', description='Suspended',
            issued_date=date.today(), effective_date=date.today(),
        )
        appeal = models.DisciplinaryAppeal.objects.create(
            action=action, appeal_date=date.today(), grounds='Test appeal',
        )
        result = DisciplineService.resolve_appeal(
            str(appeal.id), 'Upheld', {'decision_date': '2026-07-25'}, self.user,
        )
        self.assertEqual(result, 'Upheld')
        appeal.refresh_from_db()
        self.assertEqual(appeal.status, 'Upheld')
        self.assertEqual(appeal.decided_by, self.user)
        action.refresh_from_db()
        self.assertEqual(action.status, 'Enforced')

    def test_resolve_appeal_overturned_reverses_action(self):
        case = models.DisciplinaryCase.objects.create(
            employee=self.employee, incident_date=date.today(), nature_of_offense='Test',
        )
        action = models.DisciplinaryAction.objects.create(
            case=case, action_type='Termination', description='Terminated',
            issued_date=date.today(), effective_date=date.today(),
        )
        appeal = models.DisciplinaryAppeal.objects.create(
            action=action, appeal_date=date.today(), grounds='Unfair',
        )
        result = DisciplineService.resolve_appeal(
            str(appeal.id), 'Overturned', {'decision_date': '2026-07-25'}, self.user,
        )
        self.assertEqual(result, 'Overturned')
        appeal.refresh_from_db()
        self.assertEqual(appeal.status, 'Overturned')
        action.refresh_from_db()
        self.assertEqual(action.status, 'Overturned')

    def test_close_case_resolves_case(self):
        case = models.DisciplinaryCase.objects.create(
            employee=self.employee, incident_date=date.today(), nature_of_offense='Test',
        )
        DisciplineService.close_case(str(case.id), 'No further action', '2026-08-01', self.user)
        case.refresh_from_db()
        self.assertEqual(case.status, 'Resolved')
        self.assertEqual(case.resolution, 'No further action')

    def test_get_case_context_returns_all_entities(self):
        case = models.DisciplinaryCase.objects.create(
            employee=self.employee, incident_date=date.today(), nature_of_offense='Context test',
        )
        models.DisciplinaryHearing.objects.create(case=case, hearing_date=date.today())
        models.DisciplinaryAction.objects.create(
            case=case, action_type='Warning', description='Test',
            issued_date=date.today(), effective_date=date.today(),
        )
        context = DisciplineService.get_case_context()
        self.assertIn('cases', context)
        self.assertIn('hearings', context)
        self.assertIn('actions', context)
        self.assertIn('appeals', context)
        self.assertIn('severity_choices', context)
        self.assertIn('case_status_choices', context)
        self.assertIn('action_type_choices', context)
        self.assertEqual(context['severity_choices'], ['Minor', 'Major', 'Gross'])


# ── Disciplinary API ────────────────────────────────────────────────────

@override_settings(SECURE_SSL_REDIRECT=False)
class DisciplinaryAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='api_tester', password='testpass')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        dept = models.Department.objects.create(name='Engineering')
        self.employee = models.Employee.objects.create(
            emp_id='EMP030', first_name='API', last_name='Test', department=dept,
        )
        self.case_data = {
            'employee': str(self.employee.id),
            'incident_date': '2026-07-10',
            'nature_of_offense': 'API test offense',
            'severity': 'Major',
        }

    # ── DisciplinaryCase API ──
    def test_case_list_returns_200(self):
        url = reverse('hrm-disciplinary-case-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_case_create_returns_201(self):
        url = reverse('hrm-disciplinary-case-list')
        response = self.client.post(url, self.case_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('case_number', response.data)

    def test_case_detail_returns_200(self):
        case = models.DisciplinaryCase.objects.create(
            employee=self.employee, incident_date=date.today(), nature_of_offense='Detail test',
        )
        url = reverse('hrm-disciplinary-case-detail', kwargs={'pk': case.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_case_update_returns_200(self):
        case = models.DisciplinaryCase.objects.create(
            employee=self.employee, incident_date=date.today(), nature_of_offense='Original',
        )
        url = reverse('hrm-disciplinary-case-detail', kwargs={'pk': case.pk})
        response = self.client.put(url, {
            'employee': str(self.employee.id),
            'incident_date': '2026-07-11',
            'nature_of_offense': 'Updated via API',
            'severity': 'Gross',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nature_of_offense'], 'Updated via API')

    def test_case_delete_returns_204(self):
        case = models.DisciplinaryCase.objects.create(
            employee=self.employee, incident_date=date.today(), nature_of_offense='To delete',
        )
        url = reverse('hrm-disciplinary-case-detail', kwargs={'pk': case.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    # ── DisciplinaryHearing API ──
    def test_hearing_list_returns_200(self):
        url = reverse('hrm-disciplinary-hearing-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_hearing_create_returns_201(self):
        case = models.DisciplinaryCase.objects.create(
            employee=self.employee, incident_date=date.today(), nature_of_offense='Hearing test',
        )
        url = reverse('hrm-disciplinary-hearing-list')
        response = self.client.post(url, {
            'case': str(case.id),
            'hearing_date': '2026-07-15T10:00:00Z',
            'location': 'Board Room',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_hearing_detail_returns_200(self):
        case = models.DisciplinaryCase.objects.create(
            employee=self.employee, incident_date=date.today(), nature_of_offense='Test',
        )
        hearing = models.DisciplinaryHearing.objects.create(case=case, hearing_date=date.today())
        url = reverse('hrm-disciplinary-hearing-detail', kwargs={'pk': hearing.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_hearing_delete_returns_204(self):
        case = models.DisciplinaryCase.objects.create(
            employee=self.employee, incident_date=date.today(), nature_of_offense='Test',
        )
        hearing = models.DisciplinaryHearing.objects.create(case=case, hearing_date=date.today())
        url = reverse('hrm-disciplinary-hearing-detail', kwargs={'pk': hearing.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    # ── DisciplinaryAction API ──
    def test_action_list_returns_200(self):
        url = reverse('hrm-disciplinary-action-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_action_create_returns_201(self):
        case = models.DisciplinaryCase.objects.create(
            employee=self.employee, incident_date=date.today(), nature_of_offense='Action test',
        )
        url = reverse('hrm-disciplinary-action-list')
        response = self.client.post(url, {
            'case': str(case.id),
            'action_type': 'Written Warning',
            'description': 'First warning',
            'issued_date': '2026-07-10',
            'effective_date': '2026-07-11',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_action_detail_returns_200(self):
        case = models.DisciplinaryCase.objects.create(
            employee=self.employee, incident_date=date.today(), nature_of_offense='Test',
        )
        action = models.DisciplinaryAction.objects.create(
            case=case, action_type='Verbal Warning', description='Test',
            issued_date=date.today(), effective_date=date.today(),
        )
        url = reverse('hrm-disciplinary-action-detail', kwargs={'pk': action.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_action_delete_returns_204(self):
        case = models.DisciplinaryCase.objects.create(
            employee=self.employee, incident_date=date.today(), nature_of_offense='Test',
        )
        action = models.DisciplinaryAction.objects.create(
            case=case, action_type='Warning', description='Test',
            issued_date=date.today(), effective_date=date.today(),
        )
        url = reverse('hrm-disciplinary-action-detail', kwargs={'pk': action.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    # ── DisciplinaryAppeal API ──
    def test_appeal_list_returns_200(self):
        url = reverse('hrm-disciplinary-appeal-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_appeal_create_returns_201(self):
        case = models.DisciplinaryCase.objects.create(
            employee=self.employee, incident_date=date.today(), nature_of_offense='Appeal test',
        )
        action = models.DisciplinaryAction.objects.create(
            case=case, action_type='Termination', description='Terminated',
            issued_date=date.today(), effective_date=date.today(),
        )
        url = reverse('hrm-disciplinary-appeal-list')
        response = self.client.post(url, {
            'action': str(action.id),
            'appeal_date': '2026-07-20',
            'grounds': 'Unfair termination',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_appeal_detail_returns_200(self):
        case = models.DisciplinaryCase.objects.create(
            employee=self.employee, incident_date=date.today(), nature_of_offense='Test',
        )
        action = models.DisciplinaryAction.objects.create(
            case=case, action_type='Warning', description='Test',
            issued_date=date.today(), effective_date=date.today(),
        )
        appeal = models.DisciplinaryAppeal.objects.create(
            action=action, appeal_date=date.today(), grounds='Unfair',
        )
        url = reverse('hrm-disciplinary-appeal-detail', kwargs={'pk': appeal.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_appeal_delete_returns_204(self):
        case = models.DisciplinaryCase.objects.create(
            employee=self.employee, incident_date=date.today(), nature_of_offense='Test',
        )
        action = models.DisciplinaryAction.objects.create(
            case=case, action_type='Warning', description='Test',
            issued_date=date.today(), effective_date=date.today(),
        )
        appeal = models.DisciplinaryAppeal.objects.create(
            action=action, appeal_date=date.today(), grounds='Unfair',
        )
        url = reverse('hrm-disciplinary-appeal-detail', kwargs={'pk': appeal.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_unauthenticated_access_returns_401(self):
        self.client.force_authenticate(user=None)
        for endpoint in ['hrm-disciplinary-case-list', 'hrm-disciplinary-hearing-list',
                         'hrm-disciplinary-action-list', 'hrm-disciplinary-appeal-list']:
            url = reverse(endpoint)
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ── Disciplinary Integration ────────────────────────────────────────────

class DisciplinaryIntegrationTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='hr_manager', password='pass')
        dept = models.Department.objects.create(name='Engineering')
        self.employee = models.Employee.objects.create(
            emp_id='EMP100', first_name='Integration', last_name='Test', department=dept,
        )

    def test_full_disciplinary_workflow(self):
        # 1. Report a case
        result = DisciplineService.add_case({
            'employee': str(self.employee.id),
            'incident_date': '2026-07-01',
            'nature_of_offense': 'Gross insubordination',
            'severity': 'Gross',
            'description': 'Refused to follow direct order from manager',
        }, self.user)
        self.assertEqual(result, 'created')
        case = models.DisciplinaryCase.objects.get(employee=self.employee)
        self.assertEqual(case.status, 'Open')

        # 2. Schedule a hearing
        result = DisciplineService.add_hearing({
            'case_id': str(case.id),
            'hearing_date': '2026-07-15T10:00:00',
            'panel_members': 'HR Lead, Dept Head, Legal',
            'location': 'Conference Room A',
            'notes': 'Hearing scheduled per policy',
        }, self.user)
        self.assertEqual(result, 'created')
        case.refresh_from_db()
        self.assertEqual(case.status, 'Hearing Scheduled')

        # 3. Issue a disciplinary action
        result = DisciplineService.add_action({
            'case_id': str(case.id),
            'action_type': 'Final Written Warning',
            'description': 'Final written warning for insubordination',
            'issued_date': '2026-07-16',
            'effective_date': '2026-07-17',
        }, self.user)
        self.assertEqual(result, 'created')
        action = models.DisciplinaryAction.objects.get(case=case)
        self.assertEqual(action.status, 'Pending')

        # 4. Employee files an appeal
        result = DisciplineService.add_appeal({
            'action_id': str(action.id),
            'appeal_date': '2026-07-20',
            'grounds': 'Warning is too severe for first offense',
            'supporting_evidence': 'Past performance review attached',
        }, self.user)
        self.assertEqual(result, 'created')
        action.refresh_from_db()
        self.assertEqual(action.status, 'Under Appeal')
        appeal = models.DisciplinaryAppeal.objects.get(action=action)
        self.assertEqual(appeal.status, 'Submitted')

        # 5. Resolve the appeal (upheld)
        result = DisciplineService.resolve_appeal(
            str(appeal.id), 'Upheld',
            {'decision_date': '2026-07-25', 'decision_notes': 'Appeal denied, warning stands'},
            self.user,
        )
        self.assertEqual(result, 'Upheld')
        appeal.refresh_from_db()
        self.assertEqual(appeal.status, 'Upheld')
        self.assertEqual(appeal.decided_by, self.user)
        action.refresh_from_db()
        self.assertEqual(action.status, 'Enforced')

        # 6. Close the case
        DisciplineService.close_case(str(case.id), 'Final warning issued and enforced', '2026-07-26', self.user)
        case.refresh_from_db()
        self.assertEqual(case.status, 'Resolved')
        self.assertEqual(case.resolution, 'Final warning issued and enforced')
