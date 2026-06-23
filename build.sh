#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Run database migrations
python manage.py migrate

# Boot/reset default admin user
python create_admin.py

# Collect static files
python manage.py collectstatic --no-input
