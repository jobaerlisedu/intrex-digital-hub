def create_admin_user():
    from django.conf import settings
    from django.contrib.auth.hashers import make_password
    from django.contrib.auth.models import User

    if User.objects.filter(username='admin').exists():
        return

    admin_password = settings.ADMIN_PASSWORD
    if not admin_password:
        return

    User.objects.create_superuser(
        username='admin',
        email=settings.ADMIN_EMAIL,
        password=admin_password,
    )


def run_startup():
    from django.core.management import call_command

    call_command('migrate', interactive=False)
    create_admin_user()
    _init_workflows()
    _init_event_subscribers()


def _init_workflows():
    try:
        from workflow.services import initialize_standard_workflows
        initialize_standard_workflows()
    except Exception as e:
        import logging
        logging.getLogger('config.bootstrap').warning(f'Workflow init skipped: {e}')


def _init_event_subscribers():
    try:
        from config.services.notification_service import init_event_subscribers
        init_event_subscribers()
    except Exception as e:
        import logging
        logging.getLogger('config.bootstrap').warning(f'Event subscriber init skipped: {e}')
