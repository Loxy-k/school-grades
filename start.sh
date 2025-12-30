#!/bin/bash
# start.sh - Startup script for Railway

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Start Gunicorn with error handling
echo "Starting Gunicorn..."
exec gunicorn school_grades.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 3 \
    --timeout 120 \
    --log-level debug \
    --access-logfile - \
    --error-logfile -
