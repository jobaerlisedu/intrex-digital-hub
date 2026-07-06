import json
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from training import models


class CourseModelTestCase(TestCase):
    def setUp(self):
        self.course = models.Course.objects.create(title='Python Basics')

    def test_str_returns_code_and_title(self):
        self.assertIn('Python Basics', str(self.course))

    def test_is_active_defaults_true(self):
        self.assertTrue(self.course.is_active)

    def test_created_at_is_auto_set(self):
        self.assertIsNotNone(self.course.created_at)


class BatchModelTestCase(TestCase):
    def setUp(self):
        course = models.Course.objects.create(title='Python Basics')
        self.batch = models.Batch.objects.create(batch_id='BATCH-001', course=course)

    def test_str_returns_batch_id(self):
        self.assertEqual(str(self.batch), 'BATCH-001')

    def test_is_active_defaults_true(self):
        self.assertTrue(self.batch.is_active)

    def test_created_at_is_auto_set(self):
        self.assertIsNotNone(self.batch.created_at)


class RegistrationModelTestCase(TestCase):
    def setUp(self):
        course = models.Course.objects.create(title='Python Basics')
        self.registration = models.Registration.objects.create(
            student_id='STU-001', full_name='Alice Smith',
            email='alice@example.com', phone='1234567890', course=course,
        )

    def test_str_returns_student_id_and_name(self):
        self.assertEqual(str(self.registration), 'STU-001 - Alice Smith')

    def test_is_active_defaults_true(self):
        self.assertTrue(self.registration.is_active)

    def test_created_at_is_auto_set(self):
        self.assertIsNotNone(self.registration.created_at)


class TrainingPaymentModelTestCase(TestCase):
    def setUp(self):
        course = models.Course.objects.create(title='Python Basics')
        reg = models.Registration.objects.create(
            student_id='STU-001', full_name='Alice Smith',
            email='alice@example.com', phone='1234567890', course=course,
        )
        self.payment = models.Payment.objects.create(
            registration=reg, student_id='STU-001', student_name='Alice Smith',
            course_name='Python Basics',
        )

    def test_str_returns_student_id_and_status(self):
        self.assertEqual(str(self.payment), 'STU-001 - Unpaid')

    def test_is_active_defaults_true(self):
        self.assertTrue(self.payment.is_active)

    def test_created_at_is_auto_set(self):
        self.assertIsNotNone(self.payment.created_at)


class TrainingAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_course_list_returns_200(self):
        url = reverse('training-course-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_course_create_returns_201(self):
        url = reverse('training-course-list')
        data = {'title': 'Data Science'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_course_detail_returns_200(self):
        course = models.Course.objects.create(title='Web Development')
        url = reverse('training-course-detail', kwargs={'pk': course.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_course_update_returns_200(self):
        course = models.Course.objects.create(title='Old Title')
        url = reverse('training-course-detail', kwargs={'pk': course.pk})
        data = {'title': 'New Title'}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_course_delete_returns_204(self):
        course = models.Course.objects.create(title='Temporary Course')
        url = reverse('training-course-detail', kwargs={'pk': course.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_unauthenticated_access_returns_403(self):
        self.client.force_authenticate(user=None)
        url = reverse('training-course-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
