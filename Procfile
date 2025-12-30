web: python manage.py migrate && python manage.py collectstatic --noinput && gunicorn school_grades.wsgi:application --bind 0.0.0.0:$PORT --log-level debug
