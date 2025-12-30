FROM python:3.12-slim

# 1. Install ALL system dependencies for WeasyPrint
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libcairo2 \
    libgirepository-1.0-1 \
    gir1.2-pango-1.0 \
    libgobject-2.0-0 \
    shared-mime-info \
    libffi-dev \
    libcairo2-dev \
    libxml2-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Set working directory
WORKDIR /app

# 3. Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy your Django project
COPY . .

# 5. Create a proper startup script file
RUN echo '#!/bin/bash
set -e

echo "=========================================="
echo "STARTING SCHOOL GRADES SYSTEM"
echo "=========================================="

# Debug: Show environment
echo "Environment Variables:"
echo "PORT: $PORT"
if [ -n "$DATABASE_URL" ]; then
    echo "DATABASE_URL: ${DATABASE_URL:0:50}..."
else
    echo "DATABASE_URL: NOT SET - Using SQLite"
fi

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start Gunicorn - use default port if PORT is not set
PORT=${PORT:-8000}
echo "Starting Gunicorn on port $PORT..."
exec gunicorn school_grades.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 3 \
    --timeout 120 \
    --log-level info \
    --access-logfile - \
    --error-logfile -' > /start.sh && chmod +x /start.sh

# 6. Run the startup script
CMD ["/bin/bash", "/start.sh"]
