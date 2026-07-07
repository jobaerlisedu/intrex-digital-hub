#!/usr/bin/env bash
# exit on error
set -o errexit

# Activate project virtual environment (Render creates this during build)
if [ -d .venv ]; then
    source .venv/bin/activate
fi

# Start gunicorn production server
gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 4 --timeout 120 --access-logfile - --error-logfile -
