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

