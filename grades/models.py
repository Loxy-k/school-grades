from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver


class Student(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    student_id = models.CharField(max_length=20, unique=True)
    
    # FORM CHOICES - Updated to include stream
    FORM_CHOICES = [
        ('F1', 'Form 1'),
        ('F2', 'Form 2'),
        ('F3S', 'Form 3 Science'),
        ('F3H', 'Form 3 Humanities'),
        ('F4S', 'Form 4 Science'),
        ('F4H', 'Form 4 Humanities'),
    ]
    form = models.CharField(max_length=3, choices=FORM_CHOICES, default='F1')
    
    # Add a stream field for easier filtering
    STREAM_CHOICES = [
        ('SCIENCE', 'Science'),
        ('HUMANITIES', 'Humanities'),
        ('NONE', 'None'),  # For F1, F2
    ]
    stream = models.CharField(max_length=15, choices=STREAM_CHOICES, default='NONE')
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    assigned_password = models.CharField(max_length=50, null=True, blank=True,
                                         help_text='Password assigned by form teacher for initial login (plaintext)')

    def __str__(self):
        stream_display = f" ({self.get_stream_display()})" if self.stream != 'NONE' else ''
        return f"{self.first_name} {self.last_name} ({self.student_id}) - {self.get_form_display()}{stream_display}"

    @property
    def is_senior(self):
        return self.form in ('F3S', 'F3H', 'F4S', 'F4H')

    @property
    def level(self):
        return 'Senior' if self.is_senior else 'Junior'
    
    @property
    def base_form(self):
        """Return the base form without stream (F1, F2, F3, F4)"""
        if self.form in ('F3S', 'F3H'):
            return 'F3'
        elif self.form in ('F4S', 'F4H'):
            return 'F4'
        return self.form
    
    @property
    def stream_code(self):
        """Return S or H for stream"""
        return self.form[-1] if self.form in ('F3S', 'F3H', 'F4S', 'F4H') else ''
    
    def save(self, *args, **kwargs):
        # Automatically set stream based on form
        if self.form in ('F3S', 'F4S'):
            self.stream = 'SCIENCE'
        elif self.form in ('F3H', 'F4H'):
            self.stream = 'HUMANITIES'
        else:
            self.stream = 'NONE'
        super().save(*args, **kwargs)


class Subject(models.Model):
    name = models.CharField(max_length=100)
    
    # Add stream-specific subjects
    STREAM_CHOICES = [
        ('ALL', 'All Streams'),
        ('SCIENCE', 'Science Stream'),
        ('HUMANITIES', 'Humanities Stream'),
        ('JUNIOR', 'Junior Classes Only'),
        ('SENIOR', 'Senior Classes Only'),
    ]
    stream = models.CharField(max_length=15, choices=STREAM_CHOICES, default='ALL')
    
    # Add form level
    FORM_LEVEL_CHOICES = [
        ('ALL', 'All Forms'),
        ('F1', 'Form 1'),
        ('F2', 'Form 2'),
        ('F3', 'Form 3'),
        ('F4', 'Form 4'),
    ]
    form_level = models.CharField(max_length=3, choices=FORM_LEVEL_CHOICES, default='ALL')

    def __str__(self):
        stream_info = f" ({self.get_stream_display()})" if self.stream != 'ALL' else ''
        return f"{self.name}{stream_info}"


class Grade(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='grades')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    score = models.DecimalField(max_digits=5, decimal_places=2)
    
    TERM_CHOICES = [
        ('T1', 'Term 1'),
        ('T2', 'Term 2'),
        ('T3', 'Term 3'),
    ]
    term = models.CharField(max_length=2, choices=TERM_CHOICES, default='T1')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student} - {self.subject}: {self.score}"

    @property
    def letter(self):
        s = float(self.score)
        if s >= 80:
            return 'A'
        if s >= 70:
            return 'B'
        if s >= 60:
            return 'C'
        if s >= 40:
            return 'D'
        return 'F'

    def grade_label(self):
        s = float(self.score)
        if not self.student or not self.student.is_senior:
            if s >= 80:
                return 'A (EXCELLENT)'
            if s >= 70:
                return 'B (VERY GOOD)'
            if s >= 60:
                return 'C (GOOD)'
            if s >= 40:
                return 'D (PASS)'
            return 'F (FAIL)'

        # Senior classes
        if s >= 80:
            return '1 (DISTINCTION)'
        if s >= 70:
            return '2 (DISTINCTION)'
        if s >= 65:
            return '3 (STRONG CREDIT)'
        if s >= 60:
            return '4 (CREDIT)'
        if s >= 55:
            return '5 (CREDIT)'
        if s >= 50:
            return '6 (CREDIT)'
        if s >= 45:
            return '7 (PASS)'
        if s >= 40:
            return '8 (PASS)'
        return '9 (FAIL)'

    def senior_point(self):
        if not self.student or not self.student.is_senior:
            return None
        s = float(self.score)
        if s >= 80:
            return 1
        if s >= 70:
            return 2
        if s >= 65:
            return 3
        if s >= 60:
            return 4
        if s >= 55:
            return 5
        if s >= 50:
            return 6
        if s >= 45:
            return 7
        if s >= 40:
            return 8
        return 9

    def is_pass(self):
        if not self.student or not self.student.is_senior:
            return float(self.score) >= 40
        return self.senior_point() is not None and self.senior_point() <= 8


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Form Teacher'),
        ('admin', 'Administrator'),
        ('parent', 'Parent/Guardian'),
    ]
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    forms_responsible = models.CharField(
        max_length=50,  # Increased length for more forms
        blank=True, 
        null=True,
        help_text='Forms this teacher is responsible for (e.g., "F3S,F4H" or "ALL")'
    )
    
    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"
    
    @property
    def is_teacher(self):
        return self.role == 'teacher'
    
    @property
    def is_admin(self):
        return self.role == 'admin'
    
    @property
    def is_student(self):
        return self.role == 'student'
    
    @property
    def can_print_reports(self):
        return self.is_teacher or self.is_admin
    
    def get_responsible_forms(self):
        if self.forms_responsible == 'ALL':
            return ['F1', 'F2', 'F3S', 'F3H', 'F4S', 'F4H']
        elif self.forms_responsible:
            return [f.strip() for f in self.forms_responsible.split(',')]
        return []


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()