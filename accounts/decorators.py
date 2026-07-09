from functools import wraps
from django.shortcuts import redirect, render
from django.contrib.auth.models import Group


# All ERP modules with their display names and icons
ERP_MODULES = [
    ('hrm',        'HR Management',  'fa-users'),
    ('inventory',  'Inventory',      'fa-boxes-stacked'),
    ('investment', 'Investment',     'fa-chart-line'),
    ('billing',    'Billing',        'fa-file-invoice-dollar'),
    ('solutions',  'Solutions',      'fa-lightbulb'),
    ('training',   'Training',       'fa-graduation-cap'),
    ('audit_logs', 'System Audit Logs', 'fa-clock-rotate-left'),
]

ERP_MODULE_NAMES = [m[0] for m in ERP_MODULES]


def module_access(module_name):
    """
    Decorator that replaces @login_required with module-level access control.

    Usage:
        @module_access('hrm')
        def my_view(request): ...

    Rules:
      - Unauthenticated users → redirect to login
      - Superusers              → always pass through
      - Staff users             → always pass through (ERP admins)
      - Everyone else           → must be in the '{module_name}_access' Group
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # 1. Must be logged in
            if not request.user.is_authenticated:
                return redirect(f'/login/?next={request.path}')

            # 2. Superusers and staff (ERP admins) bypass all checks
            if request.user.is_superuser or request.user.is_staff:
                return view_func(request, *args, **kwargs)

            # 3. Lazy-bootstrap: ensure the group exists
            group_name = f'{module_name}_access'
            Group.objects.get_or_create(name=group_name)

            # 4. Check group membership
            if request.user.groups.filter(name=group_name).exists():
                return view_func(request, *args, **kwargs)

            # 5. Access denied
            return render(request, 'erp/403.html', {
                'module': module_name,
                'module_display': next((m[1] for m in ERP_MODULES if m[0] == module_name), module_name.title()),
            }, status=403)

        return _wrapped_view
    return decorator


def staff_required(view_func):
    """Decorator: only ERP admins (is_staff or is_superuser) can access."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f'/login/?next={request.path}')
        if request.user.is_staff or request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        return render(request, 'erp/403.html', {
            'module': 'User Management',
            'module_display': 'User Management',
        }, status=403)
    return _wrapped_view


def employee_portal_access(view_func):
    """
    Decorator for Employee Self-Service Portal views.

    Rules:
      - Unauthenticated users -> redirect to login
      - Superusers/staff bypass (ERP admins can preview)
      - Regular users must have a linked employee record via registry.Person
      - Injects `employee_data` (dict from Firestore) into kwargs
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f'/login/?next={request.path}')

        from registry.services import lookup_person_by_auth_user
        person = lookup_person_by_auth_user(request.user)
        if not person or not person.firestore_employee_id:
            if request.user.is_superuser or request.user.is_staff:
                # Staff can preview portal without employee link
                kwargs['employee_data'] = None
                return view_func(request, *args, **kwargs)
            return render(request, 'erp/403.html', {
                'module': 'Employee Portal',
                'module_display': 'Employee Portal',
            }, status=403)

        try:
            from config.firebase import db
            doc = db.collection('hrm_employees').document(person.firestore_employee_id).get()
            if doc.exists:
                emp_data = doc.to_dict()
                emp_data['id'] = doc.id
                kwargs['employee_data'] = emp_data
            else:
                kwargs['employee_data'] = None
        except Exception:
            kwargs['employee_data'] = None

        return view_func(request, *args, **kwargs)
    return _wrapped_view


def superuser_required(view_func):
    """Decorator: only system admins (is_superuser) can access."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f'/login/?next={request.path}')
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        return render(request, 'erp/403.html', {
            'module': 'Audit Logs',
            'module_display': 'System Audit Logs',
        }, status=403)
    return _wrapped_view

