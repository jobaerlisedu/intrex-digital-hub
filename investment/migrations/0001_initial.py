"""
Firebase-only architecture — no Django ORM tables.

All investment data is stored in Firestore collections (invst_*).
This migration is a no-op placeholder. No SQLite tables are created
or managed by this app.

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
