from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User, Group
from django.contrib.auth.hashers import make_password
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
import hashlib
from .decorators import staff_required, superuser_required, module_access, ERP_MODULES
from .models import log_action, get_client_ip, AuditLog, ActiveSession
from config.logger import accounts_logger


# ─────────────────────────────────────────────
# User List
# ─────────────────────────────────────────────
@staff_required
def user_list(request):
    # User Management is Django SQLite-only — Firestore replica is write-only via signals
    users = User.objects.prefetch_related('groups').order_by('-date_joined')

    # Annotate each user with their accessible module names
    user_data = []
    for user in users:
        group_names = {g.name for g in user.groups.all()}
        accessible = [
            m for m in ERP_MODULES
            if user.is_superuser or user.is_staff or f'{m[0]}_access' in group_names
        ]
        user_data.append({'user': user, 'modules': accessible})

    return render(request, 'accounts/users.html', {
        'user_data': user_data,
        'all_modules': ERP_MODULES,
    })


# ─────────────────────────────────────────────
# Create User
# ─────────────────────────────────────────────
@staff_required
def user_create(request):
    if request.method == 'POST':
        username   = request.POST.get('username', '').strip()
        password   = request.POST.get('password', '').strip()
        email      = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        is_staff   = request.POST.get('is_staff') == 'on'
        selected_modules = request.POST.getlist('modules')

        # Validation
        if not username or not password:
            messages.error(request, 'Username and password are required.')
            return render(request, 'accounts/user_form.html', {
                'all_modules': ERP_MODULES, 'action': 'Create',
                'form_data': request.POST,
            })

        if User.objects.filter(username=username).exists():
            messages.error(request, f'Username "{username}" is already taken.')
            return render(request, 'accounts/user_form.html', {
                'all_modules': ERP_MODULES, 'action': 'Create',
                'form_data': request.POST,
            })

        # Create the user
        user = User.objects.create_user(
            username=username, password=password,
            email=email, first_name=first_name,
            last_name=last_name, is_staff=is_staff,
        )

        # Assign module groups
        for module_name in selected_modules:
            if module_name in [m[0] for m in ERP_MODULES]:
                group, _ = Group.objects.get_or_create(name=f'{module_name}_access')
                user.groups.add(group)

        log_action(
            user=request.user,
            action='USER_CREATE',
            module='accounts',
            description=f"Created user '{username}' with staff={is_staff} and modules={selected_modules}",
            ip_address=get_client_ip(request)
        )

        messages.success(request, f'User "{username}" created successfully.')
        return redirect('accounts:user_list')

    return render(request, 'accounts/user_form.html', {
        'all_modules': ERP_MODULES,
        'action': 'Create',
        'form_data': {'username': '', 'first_name': '', 'last_name': '', 'email': ''},
    })


# ─────────────────────────────────────────────
# Edit User
# ─────────────────────────────────────────────
@staff_required
def user_edit(request, user_id):
    edit_user = get_object_or_404(User, id=user_id)
    user_module_names = {
        g.name[:-7] for g in edit_user.groups.all() if g.name.endswith('_access')
    }

    if request.method == 'POST':
        edit_user.email      = request.POST.get('email', '').strip()
        edit_user.first_name = request.POST.get('first_name', '').strip()
        edit_user.last_name  = request.POST.get('last_name', '').strip()

        # Only allow changing is_staff if the current user is a superuser
        if request.user.is_superuser:
            edit_user.is_staff = request.POST.get('is_staff') == 'on'

        # Change password only if provided
        new_password = request.POST.get('password', '').strip()
        if new_password:
            edit_user.set_password(new_password)
            try:
                from config.firebase import db
                db.collection('sys_users').document(edit_user.username).update({
                    'password': make_password(new_password),
                })
            except Exception as e:
                accounts_logger.warning(f"Could not sync password to Firestore for '{edit_user.username}': {e}")

        edit_user.save()

        # Reset module groups (don't touch other groups, if any)
        module_groups = Group.objects.filter(name__endswith='_access')
        edit_user.groups.remove(*module_groups)

        for module_name in request.POST.getlist('modules'):
            if module_name in [m[0] for m in ERP_MODULES]:
                group, _ = Group.objects.get_or_create(name=f'{module_name}_access')
                edit_user.groups.add(group)

        log_action(
            user=request.user,
            action='USER_EDIT',
            module='accounts',
            description=f"Edited user '{edit_user.username}' (staff={edit_user.is_staff}, modules={request.POST.getlist('modules')})",
            ip_address=get_client_ip(request)
        )

        messages.success(request, f'User "{edit_user.username}" updated successfully.')
        return redirect('accounts:user_list')

    return render(request, 'accounts/user_form.html', {
        'all_modules': ERP_MODULES,
        'action': 'Edit',
        'edit_user': edit_user,
        'user_module_names': user_module_names,
        'form_data': {
            'first_name': edit_user.first_name,
            'last_name':  edit_user.last_name,
            'email':      edit_user.email,
        },
    })


# ─────────────────────────────────────────────
# Toggle Active / Deactivate
# ─────────────────────────────────────────────
@staff_required
def user_toggle_active(request, user_id):
    target_user = get_object_or_404(User, id=user_id)

    if target_user == request.user:
        messages.error(request, 'You cannot deactivate your own account.')
        return redirect('accounts:user_list')

    if target_user.is_superuser and not request.user.is_superuser:
        messages.error(request, 'Only a superuser can deactivate another superuser.')
        return redirect('accounts:user_list')

    target_user.is_active = not target_user.is_active
    target_user.save()
    verb = 'activated' if target_user.is_active else 'deactivated'

    log_action(
        user=request.user,
        action='USER_TOGGLE_ACTIVE',
        module='accounts',
        description=f"{verb.capitalize()} user '{target_user.username}' (active={target_user.is_active})",
        ip_address=get_client_ip(request)
    )

    messages.success(request, f'User "{target_user.username}" has been {verb}.')
    return redirect('accounts:user_list')


# ─────────────────────────────────────────────
# Audit Logs & Session Monitor
# ─────────────────────────────────────────────
class FirestoreAuditLog:
    def __init__(self, data):
        self.id = data.get('id')
        self.action = data.get('action', '')
        self.module = data.get('module', '')
        self.description = data.get('description', '')
        self.ip_address = data.get('ip_address', '')
        self.sha256_hash = data.get('sha256_hash', '')
        self.before_state = data.get('before_state')
        self.after_state = data.get('after_state')
        self.user_id = data.get('user_id')
        
        username = data.get('username')
        if username and username != 'Anonymous':
            class MockUser:
                def __init__(self, name):
                    self.username = name
            self.user = MockUser(username)
        else:
            self.user = None
            
        t_val = data.get('timestamp')
        if t_val:
            from datetime import datetime
            if isinstance(t_val, str):
                try:
                    dt = datetime.strptime(t_val, '%Y-%m-%d %H:%M:%S.%f')
                except ValueError:
                    try:
                        dt = datetime.strptime(t_val, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        dt = datetime.now()
                self.timestamp = timezone.make_aware(dt) if timezone.is_naive(dt) else dt
            else:
                self.timestamp = timezone.make_aware(t_val) if timezone.is_naive(t_val) else t_val
        else:
            self.timestamp = timezone.now()


@module_access('audit_logs')
def audit_logs(request):
    active_sessions = ActiveSession.objects.select_related('user').all().order_by('-last_activity')
    
    logs = []
    use_firestore = False
    
    import sys
    if 'test' not in sys.argv:
        try:
            from config.firebase import db
            from google.cloud import firestore as google_firestore
            
            # Query recent 1000 logs from Firestore, ordered by timestamp descending
            docs = db.collection('sys_audit_logs').order_by('timestamp', direction=google_firestore.Query.DESCENDING).limit(1000).stream()
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                logs.append(FirestoreAuditLog(data))
            
            use_firestore = True
        except Exception as e:
            accounts_logger.error(f"Error fetching audit logs from Firestore: {e}")
            
    if not use_firestore:
        logs = list(AuditLog.objects.select_related('user').all().order_by('-timestamp'))
        
    # Perform an integrity check on the cryptographic hash chain
    integrity_status = "SECURE"
    altered_logs = []
    
    prev_hash = "0" * 64
    # Check from oldest to newest to verify chain validity
    for log in reversed(logs):
        if not log.sha256_hash:
            # Skip legacy log entries created before the hash chain was introduced
            continue
        payload = f"{log.user_id or ''}|{log.action}|{log.module}|{log.description}|{log.ip_address or ''}|{prev_hash}"
        expected_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()
        if log.sha256_hash != expected_hash:
            integrity_status = "COMPROMISED"
            altered_logs.append(log.id)
        prev_hash = log.sha256_hash

    # Anomaly alerts: e.g. recent failed login count (last 24 hours) or mass exports
    failed_logins = 0
    has_mass_exports = False
    
    if use_firestore:
        one_day_ago = timezone.now() - timedelta(days=1)
        for log in logs:
            if log.timestamp and log.timestamp >= one_day_ago:
                if log.action == 'LOGIN_FAILED':
                    failed_logins += 1
                if 'EXPORT' in log.action.upper():
                    has_mass_exports = True
    else:
        failed_logins = AuditLog.objects.filter(action='LOGIN_FAILED', timestamp__gte=timezone.now() - timedelta(days=1)).count()
        has_mass_exports = AuditLog.objects.filter(action__icontains='EXPORT', timestamp__gte=timezone.now() - timedelta(days=1)).exists()

    return render(request, 'accounts/audit_logs.html', {
        'logs': logs,
        'active_sessions': active_sessions,
        'integrity_status': integrity_status,
        'compromised_log_ids': altered_logs,
        'failed_logins_24h': failed_logins,
        'has_mass_exports_24h': has_mass_exports,
    })


@superuser_required
def revoke_session(request, session_id):
    from django.contrib.sessions.models import Session
    active_sess = get_object_or_404(ActiveSession, id=session_id)
    username = active_sess.user.username
    session_key = active_sess.session_key
    
    # Log the revocation
    log_action(
        user=request.user,
        action='SESSION_REVOKE',
        module='auth',
        description=f"Administratively revoked active session for user '{username}'.",
        ip_address=get_client_ip(request)
    )
    
    # Delete from Django session store
    try:
        s = Session.objects.get(session_key=session_key)
        s.delete()
    except Session.DoesNotExist:
        pass
    
    # Delete from ActiveSession registry
    active_sess.delete()
    
    messages.success(request, f"Successfully terminated session for operator @{username}.")
    return redirect('accounts:audit_logs')

