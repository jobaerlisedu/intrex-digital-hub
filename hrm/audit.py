from datetime import datetime


def enrich_with_audit(data, user=None, is_update=False):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    username = user.username if user and user.is_authenticated else 'system'
    data['updated_at'] = now
    data['updated_by'] = username
    if not is_update:
        data['created_at'] = now
        data['created_by'] = username
    return data
