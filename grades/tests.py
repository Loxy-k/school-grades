from django.test import TestCase
from django.urls import reverse
from .models import Student, Subject, Grade


class GradesSmokeTests(TestCase):
    def setUp(self):
        sub = Subject.objects.create(name='Math')
        s = Student.objects.create(first_name='T', last_name='T', student_id='T001')
        Grade.objects.create(student=s, subject=sub, score=95)

    def test_index_loads(self):
        resp = self.client.get(reverse('grades:index'))
        self.assertEqual(resp.status_code, 200)

    def test_student_detail(self):
        s = Student.objects.first()
        resp = self.client.get(reverse('grades:student_detail', args=[s.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_api_grades(self):
        resp = self.client.get(reverse('grades:api_grades'))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('grades', data)
        self.assertGreaterEqual(len(data['grades']), 1)
