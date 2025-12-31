FROM python:3.12-slim

# Minimal dependencies - no Cairo/Pango needed!
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p staticfiles media

CMD python manage.py migrate --noinput && \
    python manage.py collectstatic --noinput && \
    gunicorn school_grades.wsgi:application --bind 0.0.0.0:$PORT
