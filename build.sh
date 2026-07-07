#!/usr/bin/env bash
# exit on error
set -o errexit

# Activate project virtual environment if it exists
if [ -d .venv ]; then
    source .venv/bin/activate
fi

# Install Python dependencies
pip install -r requirements.txt

# Build frontend assets
npm install
npm run build

# Run database migrations
python manage.py migrate

# Boot/reset default admin user
python create_admin.py

# Collect static files
python manage.py collectstatic --no-input
