from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from grades.models import Student, Subject, Grade


class Command(BaseCommand):
    help = 'Seed the database with sample subjects, students, grades and a superuser (dev only)'

    def handle(self, *args, **options):
        User = get_user_model()
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'adminpass')
            self.stdout.write(self.style.SUCCESS('Created superuser: admin / adminpass'))
        else:
            self.stdout.write('Superuser already exists')

        subjects = ['Mathematics', 'Science', 'History', 'English']
        for name in subjects:
            subj, _ = Subject.objects.get_or_create(name=name)

        students_data = [
            ('Alice', 'Anderson', 'S001'),
            ('Bob', 'Brown', 'S002'),
            ('Charlie', 'Clark', 'S003'),
        ]

        # Create sample teacher/staff users for admin access
        teachers = [
            ('teacher_jane', 'Jane', 'Doe', 'teachpass'),
            ('teacher_mark', 'Mark', 'Smith', 'teachpass'),
        ]
        for username, first, last, password in teachers:
            if not User.objects.filter(username=username).exists():
                t = User.objects.create_user(username=username, email=f'{username}@example.com', password=password)
                t.is_staff = True
                t.is_active = True
                t.save()
                self.stdout.write(self.style.SUCCESS(f'Created staff user {username} (password={password})'))

        for first, last, sid in students_data:
            student, created = Student.objects.get_or_create(student_id=sid, defaults={'first_name': first, 'last_name': last})
            if created:
                self.stdout.write(f'Created student {student}')

            # create a linked Django user for the student if missing
            username = f"stu_{sid}"
            if not User.objects.filter(username=username).exists():
                u = User.objects.create_user(username=username, email=f'{sid}@example.com', password=sid)
                student.user = u
                student.save()
                self.stdout.write(self.style.SUCCESS(f'Created user {username} for student {student} (password={sid})'))

        # Create some grades
        import random
        subjects_qs = list(Subject.objects.all())
        students_qs = list(Student.objects.all())
        for s in students_qs:
            # give each student 3 random grades
            for _ in range(3):
                subj = random.choice(subjects_qs)
                score = round(random.uniform(55, 100), 2)
                Grade.objects.create(student=s, subject=subj, score=score)

        self.stdout.write(self.style.SUCCESS('Seed data created'))
