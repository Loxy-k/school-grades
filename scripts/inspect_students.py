import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_grades.settings')
import django
django.setup()
from grades.models import Student

print('Students:')
for s in Student.objects.all():
    print('ID:', s.id, 'student_id:', s.student_id, 'form:', s.get_form_display(), 'level:', s.level, 'user:', getattr(s.user, 'username', None))
