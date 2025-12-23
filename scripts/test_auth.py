import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_grades.settings')
import django
django.setup()
from django.contrib.auth import authenticate

user = authenticate(username='admin', password='adminpass')
print('authenticate(admin, adminpass) ->', user)

# Try one seeded student user
stu = authenticate(username='stu_S001', password='S001')
print('authenticate(stu_S001, S001) ->', stu)
