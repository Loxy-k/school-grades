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

# 5. Create startup script
RUN echo '#!/bin/bash\n\
set -e\n\
echo "=========================================="\n\
echo "STARTING SCHOOL GRADES SYSTEM"\n\
echo "=========================================="\n\
\n\
# Debug: Show environment\n\
echo "Environment Variables:"\n\
echo "PORT: \$PORT"\n\
if [ -n "\$DATABASE_URL" ]; then\n\
    echo "DATABASE_URL: \${DATABASE_URL:0:50}..."\n\
else\n\
    echo "DATABASE_URL: NOT SET - Using SQLite"\n\
fi\n\
\n\
# Run migrations\n\
echo "Running migrations..."\n\
python manage.py migrate --noinput\n\
\n\
# Collect static files\n\
echo "Collecting static files..."\n\
python manage.py collectstatic --noinput\n\
\n\
# Start Gunicorn\n\
echo "Starting Gunicorn on port \$PORT..."\n\
exec gunicorn school_grades.wsgi:application \\\n\
    --bind 0.0.0.0:\$PORT \\\n\
    --workers 3 \\\n\
    --timeout 120 \\\n\
    --log-level info \\\n\
    --access-logfile - \\\n\
    --error-logfile -' > /start.sh && chmod +x /start.sh

# 6. Run the startup script
CMD ["/bin/bash", "/start.sh"]
