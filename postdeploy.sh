#!/bin/bash
python manage.py migrate
echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@school.edu', 'adminpassword') if not User.objects.filter(username='admin').exists() else None" | python manage.py shell