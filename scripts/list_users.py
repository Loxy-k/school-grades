import os
import sys
from pathlib import Path

# Ensure project root is on sys.path so this script can be run directly
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_grades.settings')
import django
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
for u in User.objects.all():
    print(u.username, 'is_staff=', u.is_staff, 'is_superuser=', u.is_superuser, 'is_active=', u.is_active)
