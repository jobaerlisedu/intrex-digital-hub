from django.core.management.base import BaseCommand
from django.utils import timezone
import importlib


TASKS = {
    'hourly': [
        'config.tasks.cleanup_inactive_sessions',
    ],
    'daily': [
        'config.tasks.send_installment_reminders',
        'config.tasks.auto_post_due_journals',
        'investment.tasks.check_overdue_schedules',
        'investment.tasks.send_investment_installment_reminders',
        'investment.tasks.calculate_daily_nav',
        'investment.tasks.check_kyc_expiry',
        'investment.tasks.notify_overdue_schedules',
    ],
    'weekly': [
        'investment.tasks.check_concentration_limits',
        'investment.tasks.dispatch_weekly_performance_summary',
    ],
    'monthly': [
        'investment.tasks.accrue_monthly_fees',
        'investment.tasks.dispatch_monthly_statements',
    ],
}


def import_task(path):
    module_path, _, attr = path.rpartition('.')
    module = importlib.import_module(module_path)
    return getattr(module, attr)


class Command(BaseCommand):
    help = 'Run scheduled background tasks (replaces Celery Beat for cPanel cron)'

    def add_arguments(self, parser):
        parser.add_argument(
            'frequency',
            nargs='?',
            choices=['hourly', 'daily', 'weekly', 'monthly', 'all'],
            default=None,
            help='Which group of tasks to run',
        )

    def handle(self, *args, **options):
        freq = options['frequency']
        now = timezone.now()
        results = []

        if freq:
            groups = [freq]
        else:
            groups = ['hourly']
            if now.hour == 2:
                groups.append('daily')
            if now.weekday() == 0 and now.hour == 3:
                groups.append('weekly')
            if now.day == 1 and now.hour == 4:
                groups.append('monthly')

        for group in groups:
            if group == 'all':
                group_names = list(TASKS.keys())
            else:
                group_names = [group]
            for g in group_names:
                for task_path in TASKS.get(g, []):
                    try:
                        task_fn = import_task(task_path)
                        result = task_fn()
                        results.append(f'[{g}] {task_path}: {result}')
                        self.stdout.write(f'  OK  {task_path}')
                    except Exception as e:
                        results.append(f'[{g}] {task_path}: ERROR: {e}')
                        self.stderr.write(f'FAIL  {task_path}: {e}')

        self.stdout.write(self.style.SUCCESS(f'Ran {len(results)} tasks'))
