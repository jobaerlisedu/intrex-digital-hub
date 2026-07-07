#!/usr/bin/env bash
# exit on error
set -o errexit

# Run database migrations at startup
python manage.py migrate

# Boot/reset default admin user
python create_admin.py

# Start gunicorn production server
gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 4 --timeout 120 --access-logfile - --error-logfile -
