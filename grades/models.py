from django.db import models
from django.conf import settings


class Student(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    student_id = models.CharField(max_length=20, unique=True)
    
    # school form/class (Form 1-4). F1/F2 are junior, F3/F4 are senior
    FORM_CHOICES = [
        ('F1', 'Form 1'),
        ('F2', 'Form 2'),
        ('F3', 'Form 3'),
        ('F4', 'Form 4'),
    ]
    form = models.CharField(max_length=2, choices=FORM_CHOICES, default='F1')
     
    # Report card remarks
    form_teacher_remarks = models.TextField(blank=True, null=True)
    head_teacher_remarks = models.TextField(blank=True, null=True)
    other_requirements = models.TextField(blank=True, null=True)
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    # Optional password assigned by form teachers; used for initial student login
    assigned_password = models.CharField(max_length=50, null=True, blank=True,
                                         help_text='Password assigned by form teacher for initial login (plaintext)')
    class Meta:
        ordering = ['form', 'last_name', 'first_name']
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.student_id}) - {self.get_form_display()}"

    @property
    def is_senior(self):
        return self.form in ('F3', 'F4')

    @property
    def level(self):
        return 'Senior' if self.is_senior else 'Junior'


class Subject(models.Model):
    name = models.CharField(max_length=100)
    
    # Define which subjects belong to which forms (optional)
    FORMS_CHOICES = [
        ('ALL', 'All Forms'),
        ('F1', 'Form 1'),
        ('F2', 'Form 2'),
        ('F3', 'Form 3'),
        ('F4', 'Form 4'),
        ('JUNIOR', 'Forms 1-2'),
        ('SENIOR', 'Forms 3-4'),
    ]
    available_for = models.CharField(max_length=10, choices=FORMS_CHOICES, default='ALL')

    def __str__(self):
        return self.name


class Grade(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='grades')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    score = models.DecimalField(max_digits=5, decimal_places=2)
    
    # Teacher's name for report card
    teacher_name = models.CharField(max_length=100, blank=True, null=True)
    
    # Academic term for the grade (Term 1, Term 2, Term 3)
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
        if s >= 90:
            return 'A'
        if s >= 80:
            return 'B'
        if s >= 70:
            return 'C'
        if s >= 60:
            return 'D'
        return 'F'

    def grade_label(self):
        """Return a human-readable grade label depending on student's level.
        For junior classes (F1, F2): returns JCE grading like 'A (EXCELLENT)'.
        For senior classes (F3, F4): returns MSCE numeric grading like '1 (DISTINCTION)'.
        """
        s = float(self.score)
        if not self.student or not self.student.is_senior:
            # Junior classes (Forms 1-2): JCE grading
            if s >= 80:
                return 'A (EXCELLENT)'
            if s >= 70:
                return 'B (VERY GOOD)'
            if s >= 50:
                return 'C (GOOD)'
            if s >= 40:
                return 'D (AVERAGE)'
            return 'F (FAIL)'

        # Senior classes (Forms 3-4): MSCE numeric grading
        if s >= 80:
            return '1 (DISTINCTION)'
        if s >= 70:
            return '2 (DISTINCTION)'
        if s >= 65:
            return '3 (STRONG CREDIT)'
        if s >= 60:
            return '4 (STRONG CREDIT)'
        if s >= 55:
            return '5 (WEAK CREDIT)'
        if s >= 50:
            return '6 (WEAK CREDIT)'
        if s >= 45:
            return '7 (PASS)'
        if s >= 40:
            return '8 (PASS)'
        return '9 (FAIL)'

    def senior_point(self):
        """Return the numeric point for senior grading (1..9) or None for junior classes."""
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

    def junior_grade(self):
        """Return the letter grade for junior classes (A-F)."""
        if not self.student or self.student.is_senior:
            return None
        s = float(self.score)
        if s >= 80:
            return 'A'
        if s >= 70:
            return 'B'
        if s >= 50:
            return 'C'
        if s >= 40:
            return 'D'
        return 'F'

    def is_pass(self):
        """Return True if this grade is a pass for the student's level."""
        if not self.student or not self.student.is_senior:
            # Junior: D or better is passing (40%+)
            return float(self.score) >= 40
        # Senior: points 1-8 are passing, 9 is fail
        return self.senior_point() is not None and self.senior_point() <= 8

    def get_grade_display(self):
        """Get the appropriate grade display for report card."""
        if self.student.is_senior:
            point = self.senior_point()
            return str(point) if point else ''
        else:
            grade = self.junior_grade()
            return grade if grade else ''


