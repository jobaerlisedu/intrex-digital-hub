import json
from datetime import date
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from solutions import models
from workflow.models import WorkflowDefinition, WorkflowState, WorkflowInstance


class ProjectModelTestCase(TestCase):
    def setUp(self):
        self.project = models.Project.objects.create(
            project_code='PRJ-001', name='Website Redesign',
        )

    def test_str_returns_code_and_name(self):
        self.assertEqual(str(self.project), 'PRJ-001 - Website Redesign')

    def test_is_active_defaults_true(self):
        self.assertTrue(self.project.is_active)

    def test_created_at_is_auto_set(self):
        self.assertIsNotNone(self.project.created_at)


class TaskModelTestCase(TestCase):
    def setUp(self):
        project = models.Project.objects.create(project_code='PRJ-001', name='Website Redesign')
        phase = models.ProjectPhase.objects.create(project=project, phase_name='Design')
        self.task = models.Task.objects.create(phase=phase, task_name='Create mockups')

    def test_str_returns_task_name(self):
        self.assertEqual(str(self.task), 'Create mockups')

    def test_is_active_defaults_true(self):
        self.assertTrue(self.task.is_active)

    def test_created_at_is_auto_set(self):
        self.assertIsNotNone(self.task.created_at)


class MeetingModelTestCase(TestCase):
    def setUp(self):
        project = models.Project.objects.create(project_code='PRJ-001', name='Website Redesign')
        self.meeting = models.Meeting.objects.create(
            project=project, title='Kickoff', meeting_date=date.today(),
        )

    def test_str_returns_title_and_date(self):
        self.assertIn('Kickoff', str(self.meeting))

    def test_is_active_defaults_true(self):
        self.assertTrue(self.meeting.is_active)

    def test_created_at_is_auto_set(self):
        self.assertIsNotNone(self.meeting.created_at)


class SolutionsAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_project_list_returns_200(self):
        url = reverse('solutions-project-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_project_create_returns_201(self):
        url = reverse('solutions-project-list')
        data = {'project_code': 'PRJ-100', 'name': 'Mobile App'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_project_detail_returns_200(self):
        project = models.Project.objects.create(project_code='PRJ-002', name='E-commerce Site')
        url = reverse('solutions-project-detail', kwargs={'pk': project.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_project_update_returns_200(self):
        project = models.Project.objects.create(project_code='PRJ-003', name='Old Name')
        url = reverse('solutions-project-detail', kwargs={'pk': project.pk})
        data = {'project_code': 'PRJ-003', 'name': 'New Name'}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_project_delete_returns_204(self):
        project = models.Project.objects.create(project_code='PRJ-004', name='Temp')
        url = reverse('solutions-project-detail', kwargs={'pk': project.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_unauthenticated_access_returns_403(self):
        self.client.force_authenticate(user=None)
        url = reverse('solutions-project-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class SolutionsWorkflowTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin', password='pass')
        self.wf_def = WorkflowDefinition.objects.create(
            name='Project Lifecycle', module='solutions', entity_type='project',
        )
        self.initial_state = WorkflowState.objects.create(
            workflow=self.wf_def, state_key='not_started', label='Not Started', is_initial=True,
        )

    def test_workflow_instance_can_be_created_for_project(self):
        project = models.Project.objects.create(project_code='PRJ-WF1', name='Workflow Project')
        wf_instance = WorkflowInstance.objects.create(
            workflow=self.wf_def,
            entity_id=str(project.pk),
            entity_label=str(project),
            current_state=self.initial_state,
            started_by=self.user,
        )
        self.assertEqual(wf_instance.workflow.module, 'solutions')
        self.assertEqual(wf_instance.workflow.entity_type, 'project')
        self.assertTrue(wf_instance.is_active)

    def test_project_status_transition(self):
        project = models.Project.objects.create(
            project_code='PRJ-WF2', name='Status Change Project', status='Not Started',
        )
        project.status = 'In Progress'
        project.save()
        self.assertEqual(project.status, 'In Progress')
