from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from config.firebase import db
from config.services import KPIService

@login_required
def erp_dashboard(request):
    kpis = KPIService.get_cross_module_kpis()
    summaries = KPIService.get_module_summaries()
    quick_actions = KPIService.get_quick_actions(request.user)

    # Fetch audit logs (recent 5 system audit logs)
    audit_logs = []
    try:
        logs_stream = db.collection('sys_audit_logs').order_by('createdAt', direction='DESCENDING').limit(5).stream()
        for doc in logs_stream:
            log_data = doc.to_dict()
            log_data['id'] = doc.id
            audit_logs.append(log_data)
    except Exception:
        try:
            logs_stream = db.collection('sys_audit_logs').limit(5).stream()
            for doc in logs_stream:
                log_data = doc.to_dict()
                log_data['id'] = doc.id
                audit_logs.append(log_data)
        except Exception as e:
            print(f"Error fetching audit logs: {e}")

    # User Stats
    user_stats = {'total_users': 0, 'active_users': 0}
    try:
        from django.contrib.auth.models import User
        user_stats['total_users'] = User.objects.count()
        user_stats['active_users'] = User.objects.filter(is_active=True).count()
    except Exception as e:
        print(f"Error fetching User stats: {e}")

    # Documentation Stats
    docs_stats = {'total_pages': 0}
    try:
        import os
        from django.conf import settings
        base_docs_path = os.path.join(settings.BASE_DIR, 'docs-portal', 'docs')
        total_md_files = 0
        if os.path.exists(base_docs_path):
            for root, dirs, files in os.walk(base_docs_path):
                for file in files:
                    if file.endswith('.md'):
                        total_md_files += 1
        docs_stats['total_pages'] = total_md_files
    except Exception as e:
        print(f"Error fetching Docs stats: {e}")

    context = {
        'kpis': kpis,
        'summaries': summaries,
        'quick_actions': quick_actions,
        'user_stats': user_stats,
        'docs_stats': docs_stats,
        'audit_logs': audit_logs,
    }
    return render(request, 'erp/dashboard.html', context)


@login_required
def documentation_viewer(request, path=''):
    import os
    import markdown
    from django.conf import settings
    from django.http import Http404

    # Default to index.md if no path provided
    if not path or path == '/':
        path = 'index.md'
    
    # Ensure it ends with .md
    if not path.endswith('.md'):
        path += '.md'

    # Secure the path against directory traversal
    base_docs_path = os.path.join(settings.BASE_DIR, 'docs-portal', 'docs')
    safe_path = os.path.abspath(os.path.join(base_docs_path, path))
    
    if not safe_path.startswith(base_docs_path):
        raise Http404("Invalid documentation path.")

    if not os.path.exists(safe_path):
        raise Http404("Documentation file not found.")

    with open(safe_path, 'r', encoding='utf-8') as f:
        md_content = f.read()

    # Convert markdown to HTML with common extensions
    html_content = markdown.markdown(
        md_content,
        extensions=['extra', 'codehilite', 'toc', 'tables']
    )

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'html_content': html_content,
            'current_path': path
        })

    return render(request, 'erp/documentation.html', {
        'html_content': html_content,
        'current_path': path
    })
