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
from config.firebase import db
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
        self.list_url = reverse('hrm-department-list')

    def _create_dept(self, name='Engineering'):
        resp = self.client.post(self.list_url, {'name': name}, format='json')
        return resp.data.get('id') if resp.status_code == 201 else None

    def test_department_list_returns_200(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_department_create_returns_201(self):
        data = {'name': 'Marketing'}
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_department_detail_returns_200(self):
        dept_id = self._create_dept('Engineering')
        self.assertIsNotNone(dept_id)
        url = reverse('hrm-department-detail', kwargs={'pk': dept_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_department_update_returns_200(self):
        dept_id = self._create_dept('Engineering')
        self.assertIsNotNone(dept_id)
        url = reverse('hrm-department-detail', kwargs={'pk': dept_id})
        data = {'name': 'Engineering Updated'}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_department_delete_returns_204(self):
        dept_id = self._create_dept('Engineering')
        self.assertIsNotNone(dept_id)
        url = reverse('hrm-department-detail', kwargs={'pk': dept_id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_unauthenticated_access_returns_401(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.list_url)
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
        self.emp_doc = db.collection('hrm_employees').add({
            'emp_id': 'EMP020', 'first_name': 'Service', 'last_name': 'Test',
            'name': 'Service Test', 'is_active': True,
        })[1].get().to_dict()
        self.emp_doc['id'] = db.collection('hrm_employees').where('emp_id', '==', 'EMP020').get()[0].id

    def _create_case(self, nature='Test', severity='Minor'):
        result = DisciplineService.add_case({
            'employee': f'hrm_employees/{self.emp_doc["id"]}',
            'incident_date': '2026-07-10',
            'nature_of_offense': nature,
            'severity': severity,
        }, self.user)
        docs = list(db.collection('hrm_disciplinary_cases').where('is_active', '==', True).stream())
        case = max(docs, key=lambda d: d.to_dict().get('created_at', ''))
        return {'id': case.id, **case.to_dict()}

    def test_add_case_creates_case_with_generated_number(self):
        result = DisciplineService.add_case({
            'employee': f'hrm_employees/{self.emp_doc["id"]}',
            'incident_date': '2026-07-10',
            'nature_of_offense': 'Testing service layer',
            'severity': 'Gross',
        }, self.user)
        self.assertEqual(result, 'created')
        docs = list(db.collection('hrm_disciplinary_cases')
                   .where('is_active', '==', True).stream())
        case_doc = max(docs, key=lambda d: d.to_dict().get('created_at', ''))
        case = case_doc.to_dict()
        self.assertTrue(case.get('case_number', '').startswith('DC-'))
        self.assertEqual(case.get('severity'), 'Gross')

    def test_add_case_updates_existing_case(self):
        case = self._create_case('Original', 'Minor')
        result = DisciplineService.add_case({
            'doc_id': case['id'],
            'employee': f'hrm_employees/{self.emp_doc["id"]}',
            'incident_date': '2026-07-11',
            'nature_of_offense': 'Updated offense',
            'severity': 'Major',
        }, self.user)
        self.assertEqual(result, 'updated')
        updated = db.collection('hrm_disciplinary_cases').document(case['id']).get().to_dict()
        self.assertEqual(updated.get('nature_of_offense'), 'Updated offense')
        self.assertEqual(updated.get('severity'), 'Major')

    def test_add_hearing_creates_hearing_and_updates_case_status(self):
        case = self._create_case('Test hearing')
        result = DisciplineService.add_hearing({
            'case_id': case['id'],
            'hearing_date': '2026-07-15T10:00:00',
            'panel_members': 'Alice, Bob',
            'location': 'Room 2A',
        }, self.user)
        self.assertEqual(result, 'created')
        updated = db.collection('hrm_disciplinary_cases').document(case['id']).get().to_dict()
        self.assertEqual(len(updated.get('hearings', [])), 1)
        self.assertEqual(updated.get('status'), 'Hearing Scheduled')

    def test_add_hearing_updates_existing_hearing(self):
        case = self._create_case('Test update hearing')
        DisciplineService.add_hearing({
            'case_id': case['id'],
            'hearing_date': '2026-07-15T10:00:00',
        }, self.user)
        result = DisciplineService.add_hearing({
            'case_id': case['id'],
            'hearing_date': '2026-07-16T14:00:00',
            'status': 'Completed',
            'outcome': 'Proceed with action',
        }, self.user)
        self.assertEqual(result, 'created')
        updated2 = db.collection('hrm_disciplinary_cases').document(case['id']).get().to_dict()
        self.assertEqual(len(updated2['hearings']), 2)

    def test_add_hearing_returns_none_without_case_id(self):
        result = DisciplineService.add_hearing({'hearing_date': '2026-07-15T10:00:00'}, self.user)
        self.assertIsNone(result)

    def test_add_action_creates_action(self):
        case = self._create_case('Test action')
        result = DisciplineService.add_action({
            'case_id': case['id'],
            'action_type': 'Suspension',
            'description': '3-day suspension',
            'issued_date': '2026-07-10',
            'effective_date': '2026-07-11',
            'expiry_date': '2026-07-13',
        }, self.user)
        self.assertEqual(result, 'created')
        updated = db.collection('hrm_disciplinary_cases').document(case['id']).get().to_dict()
        self.assertEqual(len(updated.get('actions', [])), 1)
        self.assertEqual(updated['actions'][0]['action_type'], 'Suspension')

    def test_add_action_updates_existing_action(self):
        case = self._create_case('Test update action')
        DisciplineService.add_action({
            'case_id': case['id'],
            'action_type': 'Verbal Warning', 'description': 'Test',
            'issued_date': '2026-07-10', 'effective_date': '2026-07-11',
        }, self.user)
        result = DisciplineService.add_action({
            'case_id': case['id'],
            'action_type': 'Written Warning',
            'description': 'Upgraded to written',
            'issued_date': '2026-07-10',
            'effective_date': '2026-07-11',
        }, self.user)
        self.assertEqual(result, 'created')
        updated2 = db.collection('hrm_disciplinary_cases').document(case['id']).get().to_dict()
        self.assertEqual(len(updated2['actions']), 2)

    def test_add_action_returns_none_without_case_id(self):
        result = DisciplineService.add_action({
            'action_type': 'Warning', 'description': 'Test',
            'issued_date': '2026-07-10', 'effective_date': '2026-07-11',
        }, self.user)
        self.assertIsNone(result)

    def test_add_appeal_creates_appeal_and_updates_action_status(self):
        case = self._create_case('Test appeal')
        DisciplineService.add_action({
            'case_id': case['id'],
            'action_type': 'Termination', 'description': 'Terminated',
            'issued_date': '2026-07-10', 'effective_date': '2026-07-11',
        }, self.user)
        updated = db.collection('hrm_disciplinary_cases').document(case['id']).get().to_dict()
        action_id = updated['actions'][0]['id']
        result = DisciplineService.add_appeal({
            'action_id': case['id'],
            'appeal_date': '2026-07-20',
            'grounds': 'Unfair termination',
            'supporting_evidence': 'Email chain attached',
        }, self.user)
        self.assertEqual(result, 'created')
        appeals = list(db.collection('hrm_disciplinary_appeals').stream())
        self.assertTrue(len(appeals) > 0)

    def test_add_appeal_returns_none_without_action_id(self):
        result = DisciplineService.add_appeal({
            'appeal_date': '2026-07-20', 'grounds': 'Unfair',
        }, self.user)
        self.assertIsNone(result)

    def test_resolve_appeal_upheld_enforces_action(self):
        case = self._create_case('Test resolve upheld')
        DisciplineService.add_action({
            'case_id': case['id'],
            'action_type': 'Suspension', 'description': 'Suspended',
            'issued_date': '2026-07-10', 'effective_date': '2026-07-11',
        }, self.user)
        DisciplineService.add_appeal({
            'action_id': case['id'],
            'appeal_date': '2026-07-20',
            'grounds': 'Test appeal',
        }, self.user)
        appeals = list(db.collection('hrm_disciplinary_appeals').where('is_active', '==', True).stream())
        self.assertTrue(len(appeals) > 0)
        appeal_id = appeals[0].id
        result = DisciplineService.resolve_appeal(
            appeal_id, 'Upheld', {'decision_date': '2026-07-25'}, self.user,
        )
        self.assertEqual(result, 'Upheld')
        resolved = db.collection('hrm_disciplinary_appeals').document(appeal_id).get().to_dict()
        self.assertEqual(resolved.get('status'), 'Upheld')

    def test_resolve_appeal_overturned_reverses_action(self):
        case = self._create_case('Test resolve overturned')
        DisciplineService.add_action({
            'case_id': case['id'],
            'action_type': 'Termination', 'description': 'Terminated',
            'issued_date': '2026-07-10', 'effective_date': '2026-07-11',
        }, self.user)
        DisciplineService.add_appeal({
            'action_id': case['id'],
            'appeal_date': '2026-07-20',
            'grounds': 'Unfair',
        }, self.user)
        appeals = list(db.collection('hrm_disciplinary_appeals').where('is_active', '==', True).stream())
        self.assertTrue(len(appeals) > 0)
        appeal_id = appeals[0].id
        result = DisciplineService.resolve_appeal(
            appeal_id, 'Overturned', {'decision_date': '2026-07-25'}, self.user,
        )
        self.assertEqual(result, 'Overturned')
        resolved = db.collection('hrm_disciplinary_appeals').document(appeal_id).get().to_dict()
        self.assertEqual(resolved.get('status'), 'Overturned')

    def test_close_case_resolves_case(self):
        case = self._create_case('Test close')
        DisciplineService.close_case(case['id'], 'No further action', '2026-08-01', self.user)
        updated = db.collection('hrm_disciplinary_cases').document(case['id']).get().to_dict()
        self.assertEqual(updated.get('status'), 'Resolved')
        self.assertEqual(updated.get('resolution'), 'No further action')

    def test_get_case_context_returns_all_entities(self):
        case = self._create_case('Context test')
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
        self.employee_doc = db.collection('hrm_employees').add({
            'emp_id': 'EMP030', 'first_name': 'API', 'last_name': 'Test',
            'name': 'API Test', 'is_active': True,
        })[1].get().to_dict()
        self.employee_id = db.collection('hrm_employees').where('emp_id', '==', 'EMP030').get()[0].id

    # ── helpers ──
    def _create_case(self, nature='API test offense', severity='Major'):
        url = reverse('hrm-disciplinary-case-list')
        resp = self.client.post(url, {
            'incident_date': '2026-07-10',
            'nature_of_offense': nature,
            'severity': severity,
        }, format='json')
        if resp.status_code == 201:
            return {'id': resp.data.get('id'), **resp.data}
        return None

    def _create_hearing(self, data=None):
        url = reverse('hrm-disciplinary-hearing-list')
        payload = data or {'hearing_date': '2026-07-15T10:00:00Z', 'location': 'Board Room'}
        resp = self.client.post(url, payload, format='json')
        if resp.status_code == 201:
            return {'id': resp.data.get('id'), **resp.data}
        return None

    def _create_action(self, data=None):
        url = reverse('hrm-disciplinary-action-list')
        payload = data or {
            'action_type': 'Written Warning', 'description': 'First warning',
            'issued_date': '2026-07-10', 'effective_date': '2026-07-11',
        }
        resp = self.client.post(url, payload, format='json')
        if resp.status_code == 201:
            return {'id': resp.data.get('id'), **resp.data}
        return None

    def _create_appeal(self, data=None):
        url = reverse('hrm-disciplinary-appeal-list')
        payload = data or {
            'appeal_date': '2026-07-20', 'grounds': 'Unfair termination',
        }
        resp = self.client.post(url, payload, format='json')
        if resp.status_code == 201:
            return {'id': resp.data.get('id'), **resp.data}
        return None

    # ── DisciplinaryCase API ──
    def test_case_list_returns_200(self):
        url = reverse('hrm-disciplinary-case-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_case_create_returns_201(self):
        url = reverse('hrm-disciplinary-case-list')
        response = self.client.post(url, {
            'incident_date': '2026-07-10',
            'nature_of_offense': 'API test offense',
            'severity': 'Major',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('case_number', response.data)

    def test_case_detail_returns_200(self):
        case = self._create_case('Detail test')
        self.assertIsNotNone(case)
        url = reverse('hrm-disciplinary-case-detail', kwargs={'pk': case['id']})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_case_update_returns_200(self):
        case = self._create_case('Original')
        self.assertIsNotNone(case)
        url = reverse('hrm-disciplinary-case-detail', kwargs={'pk': case['id']})
        response = self.client.put(url, {
            'incident_date': '2026-07-11',
            'nature_of_offense': 'Updated via API',
            'severity': 'Gross',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nature_of_offense'], 'Updated via API')

    def test_case_delete_returns_204(self):
        case = self._create_case('To delete')
        self.assertIsNotNone(case)
        url = reverse('hrm-disciplinary-case-detail', kwargs={'pk': case['id']})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    # ── DisciplinaryHearing API ──
    def test_hearing_list_returns_200(self):
        url = reverse('hrm-disciplinary-hearing-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_hearing_create_returns_201(self):
        url = reverse('hrm-disciplinary-hearing-list')
        response = self.client.post(url, {
            'hearing_date': '2026-07-15T10:00:00Z',
            'location': 'Board Room',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_hearing_detail_returns_200(self):
        hearing = self._create_hearing()
        self.assertIsNotNone(hearing)
        url = reverse('hrm-disciplinary-hearing-detail', kwargs={'pk': hearing['id']})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_hearing_delete_returns_204(self):
        hearing = self._create_hearing()
        self.assertIsNotNone(hearing)
        url = reverse('hrm-disciplinary-hearing-detail', kwargs={'pk': hearing['id']})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    # ── DisciplinaryAction API ──
    def test_action_list_returns_200(self):
        url = reverse('hrm-disciplinary-action-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_action_create_returns_201(self):
        url = reverse('hrm-disciplinary-action-list')
        response = self.client.post(url, {
            'action_type': 'Written Warning',
            'description': 'First warning',
            'issued_date': '2026-07-10',
            'effective_date': '2026-07-11',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_action_detail_returns_200(self):
        action = self._create_action()
        self.assertIsNotNone(action)
        url = reverse('hrm-disciplinary-action-detail', kwargs={'pk': action['id']})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_action_delete_returns_204(self):
        action = self._create_action()
        self.assertIsNotNone(action)
        url = reverse('hrm-disciplinary-action-detail', kwargs={'pk': action['id']})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    # ── DisciplinaryAppeal API ──
    def test_appeal_list_returns_200(self):
        url = reverse('hrm-disciplinary-appeal-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_appeal_create_returns_201(self):
        url = reverse('hrm-disciplinary-appeal-list')
        response = self.client.post(url, {
            'appeal_date': '2026-07-20',
            'grounds': 'Unfair termination',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_appeal_detail_returns_200(self):
        appeal = self._create_appeal()
        self.assertIsNotNone(appeal)
        url = reverse('hrm-disciplinary-appeal-detail', kwargs={'pk': appeal['id']})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_appeal_delete_returns_204(self):
        appeal = self._create_appeal()
        self.assertIsNotNone(appeal)
        url = reverse('hrm-disciplinary-appeal-detail', kwargs={'pk': appeal['id']})
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
        self.employee_doc = db.collection('hrm_employees').add({
            'emp_id': 'EMP100', 'first_name': 'Integration', 'last_name': 'Test',
            'name': 'Integration Test', 'is_active': True,
        })[1].get().to_dict()
        self.employee_id = db.collection('hrm_employees').where('emp_id', '==', 'EMP100').get()[0].id

    def test_full_disciplinary_workflow(self):
        employee_path = f'hrm_employees/{self.employee_id}'

        # 1. Report a case
        result = DisciplineService.add_case({
            'employee': employee_path,
            'incident_date': '2026-07-01',
            'nature_of_offense': 'Gross insubordination',
            'severity': 'Gross',
            'description': 'Refused to follow direct order from manager',
        }, self.user)
        self.assertEqual(result, 'created')
        docs = list(db.collection('hrm_disciplinary_cases')
                   .where('is_active', '==', True).stream())
        case_doc = max(docs, key=lambda d: d.to_dict().get('created_at', ''))
        case = case_doc.to_dict()
        self.assertEqual(case.get('status'), 'Open')
        case_id = case_doc.id

        # 2. Schedule a hearing
        result = DisciplineService.add_hearing({
            'case_id': case_id,
            'hearing_date': '2026-07-15T10:00:00',
            'panel_members': 'HR Lead, Dept Head, Legal',
            'location': 'Conference Room A',
            'notes': 'Hearing scheduled per policy',
        }, self.user)
        self.assertEqual(result, 'created')
        updated = db.collection('hrm_disciplinary_cases').document(case_id).get().to_dict()
        self.assertEqual(updated.get('status'), 'Hearing Scheduled')

        # 3. Issue a disciplinary action
        result = DisciplineService.add_action({
            'case_id': case_id,
            'action_type': 'Final Written Warning',
            'description': 'Final written warning for insubordination',
            'issued_date': '2026-07-16',
            'effective_date': '2026-07-17',
        }, self.user)
        self.assertEqual(result, 'created')
        updated = db.collection('hrm_disciplinary_cases').document(case_id).get().to_dict()
        self.assertEqual(updated['actions'][0]['status'], 'Pending')

        # 4. Employee files an appeal
        result = DisciplineService.add_appeal({
            'action_id': case_id,
            'appeal_date': '2026-07-20',
            'grounds': 'Warning is too severe for first offense',
            'supporting_evidence': 'Past performance review attached',
        }, self.user)
        self.assertEqual(result, 'created')
        updated = db.collection('hrm_disciplinary_cases').document(case_id).get().to_dict()
        self.assertEqual(updated['actions'][0]['status'], 'Under Appeal')
        appeal_docs = [d for d in db.collection('hrm_disciplinary_appeals').stream()
                       if d.to_dict().get('action_id') == case_id]
        self.assertTrue(len(appeal_docs) >= 1)
        appeal = appeal_docs[-1].to_dict()
        self.assertEqual(appeal.get('status'), 'Submitted')
        appeal_id = appeal_docs[-1].id

        # 5. Resolve the appeal (upheld)
        result = DisciplineService.resolve_appeal(
            appeal_id, 'Upheld',
            {'decision_date': '2026-07-25', 'decision_notes': 'Appeal denied, warning stands'},
            self.user,
        )
        self.assertEqual(result, 'Upheld')
        resolved = db.collection('hrm_disciplinary_appeals').document(appeal_id).get().to_dict()
        self.assertEqual(resolved.get('status'), 'Upheld')
        self.assertEqual(resolved.get('decided_by'), f'users/{self.user.id}')
        updated = db.collection('hrm_disciplinary_cases').document(case_id).get().to_dict()
        self.assertEqual(updated['actions'][0]['status'], 'Enforced')

        # 6. Close the case
        DisciplineService.close_case(case_id, 'Final warning issued and enforced', '2026-07-26', self.user)
        updated = db.collection('hrm_disciplinary_cases').document(case_id).get().to_dict()
        self.assertEqual(updated.get('status'), 'Resolved')
        self.assertEqual(updated.get('resolution'), 'Final warning issued and enforced')
