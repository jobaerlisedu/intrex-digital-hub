import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from config.bootstrap import create_admin_user

create_admin_user()
