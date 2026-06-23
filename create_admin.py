import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User

try:
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        print("SUCCESS: Superuser 'admin' created.")
    else:
        user = User.objects.get(username='admin')
        user.set_password('admin123')
        user.save()
        print("SUCCESS: Superuser 'admin' already existed, password reset to 'admin123'.")
except Exception as e:
    print(f"ERROR: {str(e)}")
