# Quick test for student login flows
import os
import django
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_grades.settings')
django.setup()
from django.test import Client
from grades.models import Student
from django.contrib.auth import get_user_model

User = get_user_model()
client = Client()

# Ensure student exists
stu, created = Student.objects.get_or_create(student_id='S001', defaults={'first_name':'Alice','last_name':'Test','form':'F1'})
if created:
    print('Created student S001')
# remove linked user if any
if stu.user:
    stu.user.delete()
    stu.user = None
    stu.save()
    print('Removed linked user')

# Test 1: login using student_id with any password -> should create user and set password to student_id
resp = client.post('/student/login/', {'username':'S001','password':'whatever'})
print('Test1 status_code', resp.status_code)
if resp.status_code in (302,303):
    print('Redirected to', resp['Location'])
else:
    print('Content snippet:', resp.content[:500])

# Check user created and password set
stu = Student.objects.get(student_id='S001')
if stu.user:
    print('Linked user exists:', stu.user.username)
    # try login with student_id password
    client.logout()
    resp2 = client.post('/student/login/', {'username': f'stu_{stu.student_id}','password': stu.student_id})
    print('Test1 second login status', resp2.status_code)

# Test 2: assigned password using firstname
stu.assigned_password = 'teachpass'
stu.save()
print('Assigned password set to teachpass')
client.logout()
resp3 = client.post('/student/login/', {'username':stu.first_name,'password':'teachpass'})
print('Test2 status_code', resp3.status_code)
if resp3.status_code in (302,303):
    print('Redirected to', resp3['Location'])
else:
    print('Content snippet:', resp3.content[:500])

print('Done')
