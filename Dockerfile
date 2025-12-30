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

# 5. Run commands directly
CMD python manage.py migrate --noinput && \
    python manage.py collectstatic --noinput && \
    PORT=${PORT:-8000} && \
    gunicorn school_grades.wsgi:application \
        --bind 0.0.0.0:$PORT \
        --workers 3 \
        --timeout 120 \
        --log-level info \
        --access-logfile - \
        --error-logfile -
