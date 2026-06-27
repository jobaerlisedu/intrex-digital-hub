from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from accounts.models import AuditLog, ActiveSession, log_action
import hashlib

class SecurityModuleTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="test_admin", password="password123", is_superuser=True)
        self.client = Client()
        self.client.force_login(self.user)

    def test_log_immutability(self):
        """
        Verify that update or delete operations on AuditLog raise PermissionDenied.
        """
        log = AuditLog.objects.create(
            user=self.user,
            action="TEST_ACTION",
            module="test",
            description="Immutable log test entry."
        )
        self.assertIsNotNone(log.id)

        # Attempt to Update log
        log.description = "Updated description"
        with self.assertRaises(PermissionDenied):
            log.save()

        # Attempt to Delete log
        with self.assertRaises(PermissionDenied):
            log.delete()

    def test_cryptographic_hash_chaining(self):
        """
        Verify that each AuditLog SHA-256 hash chains to the previous record.
        """
        log1 = AuditLog.objects.create(
            user=self.user,
            action="ACTION_1",
            module="auth",
            description="First entry in chain."
        )
        self.assertIsNotNone(log1.sha256_hash)

        log2 = AuditLog.objects.create(
            user=self.user,
            action="ACTION_2",
            module="auth",
            description="Second entry in chain."
        )
        self.assertIsNotNone(log2.sha256_hash)

        # Expected hash check
        payload = f"{self.user.id}|ACTION_2|auth|Second entry in chain.||{log1.sha256_hash}"
        expected_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()
        self.assertEqual(log2.sha256_hash, expected_hash)

    def test_session_management_and_revocation(self):
        """
        Verify active session tracking and superuser session revocation.
        """
        # 1. Establish session in active session tracking
        session_key = self.client.session.session_key
        active_sess = ActiveSession.objects.create(
            user=self.user,
            session_key=session_key,
            ip_address="127.0.0.1",
            user_agent="Django-Test-Agent"
        )
        self.assertEqual(ActiveSession.objects.count(), 1)

        # 2. Revoke session via URL
        url = reverse('accounts:revoke_session', args=[active_sess.id])
        res = self.client.post(url)
        self.assertEqual(res.status_code, 302)  # Redirects to audit_logs

        # 3. Assert session records are deleted
        self.assertEqual(ActiveSession.objects.count(), 0)
