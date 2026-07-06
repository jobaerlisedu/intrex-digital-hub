from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.core.exceptions import PermissionDenied
from django.db.models.signals import pre_delete
import hashlib

class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action = models.CharField(max_length=100)  # e.g., 'LOGIN', 'USER_CREATE', 'EXPORT_REPORT'
    module = models.CharField(max_length=50)   # e.g., 'hrm', 'inventory', 'accounts'
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    before_state = models.JSONField(null=True, blank=True)
    after_state = models.JSONField(null=True, blank=True)
    sha256_hash = models.CharField(max_length=64, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise PermissionDenied("Audit logs are immutable and cannot be updated.")
        
        # Cryptographic Hash Chain Calculation
        prev_hash = "0" * 64
        use_firestore = False
        import sys
        if 'test' not in sys.argv:
            try:
                from config.firebase import db
                from google.cloud import firestore as google_firestore
                logs_ref = db.collection('sys_audit_logs')
                query = logs_ref.order_by('timestamp', direction=google_firestore.Query.DESCENDING).limit(1)
                docs = list(query.stream())
                if docs:
                    prev_hash = docs[0].to_dict().get('sha256_hash') or "0" * 64
                use_firestore = True
            except Exception as e:
                print(f"Warning: Could not fetch last hash chain from Firestore, falling back to SQLite: {e}")
        
        if not use_firestore:
            last_log = AuditLog.objects.order_by('-id').first()
            prev_hash = last_log.sha256_hash if last_log and last_log.sha256_hash else "0" * 64

        payload = f"{self.user_id or ''}|{self.action}|{self.module}|{self.description}|{self.ip_address or ''}|{prev_hash}"
        self.sha256_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()
        super().save(*args, **kwargs)

        # Write to Firestore
        if use_firestore:
            try:
                from config.firebase import db
                from google.cloud import firestore as google_firestore
                
                db.collection('sys_audit_logs').add({
                    'user_id': self.user_id,
                    'username': self.user.username if self.user else 'Anonymous',
                    'action': self.action,
                    'module': self.module,
                    'description': self.description,
                    'ip_address': self.ip_address,
                    'before_state': self.before_state,
                    'after_state': self.after_state,
                    'sha256_hash': self.sha256_hash,
                    'timestamp': google_firestore.SERVER_TIMESTAMP
                })
            except Exception as e:
                print(f"Failed to write audit log to Firestore: {e}")

    def __str__(self):
        user_str = self.user.username if self.user else "Anonymous"
        return f"{user_str} - {self.action} at {self.timestamp}"


@receiver(pre_delete, sender=AuditLog)
def block_audit_log_delete(sender, instance, **kwargs):
    raise PermissionDenied("Audit logs are immutable and cannot be deleted.")


class ActiveSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='active_sessions')
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.session_key[:8]}..."


def get_client_ip(request):
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_action(user, action, module, description, ip_address=None, before_state=None, after_state=None):
    """
    Utility function to log a system audit action.
    """
    try:
        AuditLog.objects.create(
            user=user if user and user.is_authenticated else None,
            action=action,
            module=module,
            description=description,
            ip_address=ip_address,
            before_state=before_state,
            after_state=after_state
        )
    except Exception as e:
        print(f"Failed to write audit log: {e}")


def log_action_async(user, action, module, description, ip_address=None, before_state=None, after_state=None):
    """
    Asynchronously write logs to prevent request latency, except during tests to avoid SQLite database locks.
    """
    import sys
    if 'test' in sys.argv:
        log_action(user, action, module, description, ip_address, before_state, after_state)
    else:
        import threading
        t = threading.Thread(
            target=log_action,
            args=(user, action, module, description, ip_address, before_state, after_state),
            daemon=True
        )
        t.start()


# ────────────────────────────────────────────────────────
# Signals to log Auth events
# ────────────────────────────────────────────────────────

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    ip = get_client_ip(request)
    log_action_async(
        user=user,
        action='LOGIN',
        module='auth',
        description=f"User '{user.username}' successfully logged in.",
        ip_address=ip
    )

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    ip = get_client_ip(request)
    log_action_async(
        user=user,
        action='LOGOUT',
        module='auth',
        description=f"User '{user.username if user else 'Unknown'}' logged out.",
        ip_address=ip
    )

@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    ip = get_client_ip(request)
    username = credentials.get('username', 'Unknown')
    log_action_async(
        user=None,
        action='LOGIN_FAILED',
        module='auth',
        description=f"Failed login attempt for username '{username}'.",
        ip_address=ip
    )
