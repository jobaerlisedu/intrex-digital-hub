import os
import time
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from accounts.models import AuditLog


@login_required
def erp_dashboard(request):
    from config.services import KPIService

    kpis = KPIService.get_cross_module_kpis()
    summaries = KPIService.get_module_summaries()
    quick_actions = KPIService.get_quick_actions(request.user)

    audit_logs = list(AuditLog.objects.select_related('user').order_by('-timestamp')[:5].values(
        'user__username', 'action', 'module', 'description', 'timestamp',
    ))
    for log in audit_logs:
        log['username'] = log.pop('user__username') or 'Anonymous'

    from django.contrib.auth.models import User
    user_stats = {
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
    }

    from django.conf import settings
    docs_stats = {'total_pages': 0}
    base_docs_path = os.path.join(settings.BASE_DIR, 'docs-portal', 'docs')
    if os.path.exists(base_docs_path):
        total_md_files = 0
        for root, dirs, files in os.walk(base_docs_path):
            total_md_files += sum(1 for f in files if f.endswith('.md'))
        docs_stats['total_pages'] = total_md_files

    context = {
        'kpis': kpis,
        'summaries': summaries,
        'quick_actions': quick_actions,
        'user_stats': user_stats,
        'docs_stats': docs_stats,
        'audit_logs': audit_logs,
    }
    return render(request, 'erp/dashboard.html', context)


def health_check(request):
    status = {"status": "healthy", "timestamp": time.time()}
    code = 200

    # Database
    try:
        from django.db import connection
        connection.ensure_connection()
        status["database"] = "connected"
    except Exception as e:
        status["database"] = f"disconnected: {e}"
        status["status"] = "degraded"
        code = 503

    # Redis / Cache
    try:
        from django.core.cache import cache
        cache.set('_health_check', 1, 5)
        if cache.get('_health_check') != 1:
            raise RuntimeError('cache write/read mismatch')
        status["cache"] = "connected"
    except Exception as e:
        status["cache"] = f"disconnected: {e}"
        if code == 200:
            status["status"] = "degraded"
            code = 503

    # Celery worker (lightweight ping via Redis stats — full task ping is heavy)
    from django.conf import settings
    celery_broker = getattr(settings, 'CELERY_BROKER_URL', '')
    status["celery_broker"] = "configured" if celery_broker else "not configured"

    return JsonResponse(status, status=code)


@login_required
def documentation_viewer(request, path=''):
    import markdown
    import re
    from django.conf import settings
    from django.http import Http404

    if not path or path == '/':
        path = 'index.md'

    if not path.endswith('.md'):
        path += '.md'

    base_docs_path = os.path.join(settings.BASE_DIR, 'docs-portal', 'docs')
    safe_path = os.path.abspath(os.path.join(base_docs_path, path))

    if not safe_path.startswith(base_docs_path):
        raise Http404("Invalid documentation path.")

    if not os.path.exists(safe_path):
        raise Http404("Documentation file not found.")

    with open(safe_path, 'r', encoding='utf-8') as f:
        md_content = f.read()

    html_content = markdown.markdown(
        md_content,
        extensions=['extra', 'codehilite', 'toc', 'tables'],
        extension_configs={
            'extra': {
                'markdown.extensions.extra': {
                    'enable_raw_html': False
                }
            }
        }
    )
    html_content = re.sub(r'<script[\s\S]*?<\/script>', '', html_content, flags=re.IGNORECASE)
    html_content = re.sub(r'<iframe[\s\S]*?<\/iframe>', '', html_content, flags=re.IGNORECASE)
    html_content = re.sub(r'<object[\s\S]*?<\/object>', '', html_content, flags=re.IGNORECASE)
    html_content = re.sub(r'<embed[\s\S]*?<\/embed>', '', html_content, flags=re.IGNORECASE)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'html_content': html_content,
            'current_path': path
        })

    return render(request, 'erp/documentation.html', {
        'html_content': html_content,
        'current_path': path
    })
