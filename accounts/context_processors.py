from .decorators import ERP_MODULE_NAMES


def user_modules(request):
    """
    Adds to every template context:
      - `user_modules` (set of module names) — used by sidebar
      - `is_portal_employee` (bool) — whether the logged-in user has a linked employee record
    """
    ctx = {'user_modules': set(), 'is_portal_employee': False}

    if not request.user.is_authenticated:
        return ctx

    # Check if user has a linked employee record via registry.Person
    try:
        from registry.models import Person
        ctx['is_portal_employee'] = Person.objects.filter(
            auth_user=request.user, person_type='employee', is_active=True
        ).exclude(firestore_employee_id='').exists()
    except Exception:
        pass

    # Superusers and staff see everything
    if request.user.is_superuser or request.user.is_staff:
        ctx['user_modules'] = set(ERP_MODULE_NAMES)
        ctx['is_portal_employee'] = True
        return ctx

    # Regular users: derive access from their groups
    accessible = set()
    for group in request.user.groups.all():
        name = group.name
        if name.endswith('_access'):
            module = name[:-7]
            if module in ERP_MODULE_NAMES:
                accessible.add(module)

    ctx['user_modules'] = accessible
    return ctx
