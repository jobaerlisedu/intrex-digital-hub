from .decorators import ERP_MODULE_NAMES


def user_modules(request):
    ctx = {'user_modules': set()}

    if not request.user.is_authenticated:
        return ctx

    if request.user.is_superuser or request.user.is_staff:
        ctx['user_modules'] = set(ERP_MODULE_NAMES)
        return ctx

    accessible = set()
    for group in request.user.groups.all():
        name = group.name
        if name.endswith('_access'):
            module = name[:-7]
            if module in ERP_MODULE_NAMES:
                accessible.add(module)

    ctx['user_modules'] = accessible
    return ctx
