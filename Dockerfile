FROM python:3.12-slim

# 1. Install system dependencies
RUN apt-get update && apt-get install -y \
    # PDF generation dependencies
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    # Cairo development for pycairo (if needed)
    libcairo2-dev \
    # pkg-config for building Python packages
    pkg-config \
    # Build tools
    gcc \
    g++ \
    python3-dev \
    # PostgreSQL client
    libpq-dev \
    # XML libraries
    libxml2-dev \
    libxslt1-dev \
    # Clean up
    && rm -rf /var/lib/apt/lists/*

# 2. Set working directory
WORKDIR /app

# 3. Copy requirements first (better layer caching)
COPY requirements.txt .

# 4. Install Python dependencies (don't upgrade pip to avoid warnings)
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy application code
COPY . .

# 6. Create staticfiles directory if it doesn't exist
RUN mkdir -p staticfiles

# 7. Run the application
CMD python manage.py migrate --noinput && \
    python manage.py collectstatic --noinput && \
    gunicorn school_grades.wsgi:application \
        --bind 0.0.0.0:$PORT \
        --workers 3 \
        --timeout 120 \
        --log-level info \
        --access-logfile - \
        --error-logfile -
