#!/usr/bin/env bash
# exit on error
set -o errexit

# Run database migrations at startup
python manage.py migrate

# Boot/reset default admin user
python create_admin.py

# Start the Django server binding to the Render-allocated port
python manage.py runserver 0.0.0.0:${PORT:-8000}
