"""
Investment module initial migration — Django ORM tables are
created by subsequent migrations.

Migration Plan
──────────────
Before deploying, run:
  python manage.py migrate investment zero --fake
  python manage.py migrate investment

This unlinks the old ORM tables (which can be dropped manually
if no other app references them) and applies this empty migration.
"""

from django.db import migrations


class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = []
