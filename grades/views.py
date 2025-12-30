# grades/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required,user_passes_test
from django.utils import timezone
from django.template.loader import render_to_string
from django.db.models import Avg
import os
import io
from zipfile import ZipFile

# Import your models
from .models import Student, Subject, Grade

# Set WeasyPrint DLL path at the module level (for local development only)
if os.name == 'nt':  # Windows
    os.environ['WEASYPRINT_DLL_DIRECTORIES'] = r'C:\Program Files\GTK3-Runtime Win64\bin'
    os.environ['PATH'] = r'C:\Program Files\GTK3-Runtime Win64\bin;' + os.environ.get('PATH', '')


def _get_logged_student(request):
    """Helper function to get the logged-in student."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return None
    try:
        return Student.objects.get(user=user)
    except Student.DoesNotExist:
        return None


def index(request):
    """School homepage / landing page."""
    return render(request, 'grades/home.html')


def student_detail(request, pk):
    """View individual student details."""
    student = get_object_or_404(Student, pk=pk)
    grades = student.grades.select_related('subject').all()
    return render(request, 'grades/student_detail.html', {
        'student': student,
        'grades': grades
    })


def api_grades(request):
    """Return a JSON list of grades with student and subject info."""
    qs = Grade.objects.select_related('student', 'subject').all()
    data = []
    for g in qs:
        data.append({
            'id': g.id,
            'student': {
                'id': g.student.id,
                'student_id': g.student.student_id,
                'name': f'{g.student.first_name} {g.student.last_name}'
            },
            'subject': g.subject.name,
            'score': float(g.score),
            'letter': g.letter,
            'created_at': g.created_at.isoformat(),
        })

    return JsonResponse({'grades': data})


def student_login(request):
    """Student login using Django auth (username/password)."""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if not username or not password:
            return render(request, 'grades/student_login.html', {
                'error': 'Please provide username and password'
            })

        user = authenticate(request, username=username, password=password)
        
        if user is None:
            # Fallback: support two student login methods
            student = None
            
            # Try match by student_id first
            try:
                student = Student.objects.get(student_id=username)
            except Student.DoesNotExist:
                # Try match by first name (case-insensitive) and assigned_password
                try:
                    student = Student.objects.get(
                        first_name__iexact=username,
                        assigned_password=password
                    )
                except Student.DoesNotExist:
                    student = None

            if student:
                User = get_user_model()
                
                # Ensure there's a linked Django user
                if student.user:
                    u = student.user
                else:
                    username_field = f"stu_{student.student_id}"
                    if not User.objects.filter(username=username_field).exists():
                        u = User.objects.create_user(
                            username=username_field,
                            email=f'{student.student_id}@example.com'
                        )
                        u.set_unusable_password()
                        u.save()
                        student.user = u
                        student.save()
                    else:
                        u = User.objects.get(username=username_field)

                # If the student matched via the student's ID used as password
                if student and student.first_name.lower() == username.lower() and password == student.student_id:
                    # Set the user's password to the student_id and log them in
                    u.set_password(password)
                    u.save()
                    login(request, u, backend='django.contrib.auth.backends.ModelBackend')
                    return redirect('grades:dashboard')

                # If the student matched via teacher-assigned password
                if (student and student.assigned_password and 
                    student.first_name.lower() == username.lower() and 
                    student.assigned_password == password):
                    
                    # Ensure linked user exists
                    username_field = f"stu_{student.student_id}"
                    User = get_user_model()
                    if not student.user:
                        if not User.objects.filter(username=username_field).exists():
                            u = User.objects.create_user(
                                username=username_field,
                                email=f'{student.student_id}@example.com'
                            )
                        else:
                            u = User.objects.get(username=username_field)
                        student.user = u
                        student.save()
                    else:
                        u = student.user

                    # Set the user's password to the assigned password and log them in
                    u.set_password(password)
                    u.save()
                    login(request, u, backend='django.contrib.auth.backends.ModelBackend')
                    return redirect('grades:dashboard')

                # If the user has no usable password, auto-assign temporary password
                if not u.has_usable_password():
                    temp_password = student.student_id
                    u.set_password(temp_password)
                    u.save()
                    login(request, u, backend='django.contrib.auth.backends.ModelBackend')
                    return redirect('grades:dashboard')

                # User has a usable password but authentication failed
                return render(request, 'grades/student_login.html', {
                    'error': 'Invalid credentials'
                })

            return render(request, 'grades/student_login.html', {
                'error': 'Invalid credentials'
            })

        login(request, user)
        return redirect('grades:dashboard')

    return render(request, 'grades/student_login.html')


def student_logout(request):
    """Logout the current user."""
    logout(request)
    return redirect('grades:index')


@login_required
def dashboard(request):
    """Student dashboard."""
    student = _get_logged_student(request)
    if not student:
        return redirect('grades:student_login')
    return render(request, 'grades/dashboard.html', {'student': student})


@login_required
def student_grades(request):
    """View student grades for a specific term."""
    student = _get_logged_student(request)
    if not student:
        return redirect('grades:student_login')
    
    # Allow selecting a term via ?term=T1|T2|T3 (default T1)
    term = request.GET.get('term', 'T1')
    term_display = {'T1': 'Term 1', 'T2': 'Term 2', 'T3': 'Term 3'}.get(term, term)
    
    # Get all standard subjects for the report card
    standard_subjects = [
        'Agriculture', 'Bible Knowledge', 'Biology', 'Chemistry', 
        'Chichewa', 'English', 'Geography', 'History', 
        'Mathematics', 'Physics', 'Social & Life Skills'
    ]
    
    # Get or create subject records and grades
    subjects_data = []
    for subject_name in standard_subjects:
        subject, created = Subject.objects.get_or_create(name=subject_name)
        
        # Try to get grade for this student and subject
        grade = Grade.objects.filter(
            student=student, 
            subject=subject,
            term=term
        ).first()
        
        if grade:
            score = float(grade.score)
            # Calculate position in this subject
            subject_position = Grade.objects.filter(
                subject=subject,
                term=term,
                student__form=student.form,
                score__gt=grade.score
            ).count() + 1
            
            # Determine grade display based on student level
            if student.is_senior:
                # Senior (Form 3-4): MSCE grading
                if score >= 80:
                    short_grade = '1'
                    comment = 'DISTINCTION'
                elif score >= 70:
                    short_grade = '2'
                    comment = 'DISTINCTION'
                elif score >= 65:
                    short_grade = '3'
                    comment = 'STRONG CREDIT'
                elif score >= 60:
                    short_grade = '4'
                    comment = 'STRONG CREDIT'
                elif score >= 55:
                    short_grade = '5'
                    comment = 'CREDIT'
                elif score >= 50:
                    short_grade = '6'
                    comment = 'CREDIT'
                elif score >= 45:
                    short_grade = '7'
                    comment = 'PASS'
                elif score >= 40:
                    short_grade = '8'
                    comment = 'PASS'
                else:
                    short_grade = '9'
                    comment = 'FAIL'
            else:
                # Junior (Form 1-2): JCE grading
                if score >= 80:
                    short_grade = 'A'
                    comment = 'EXCELLENT'
                elif score >= 70:
                    short_grade = 'B'
                    comment = 'VERY GOOD'
                elif score >= 50:
                    short_grade = 'C'
                    comment = 'GOOD'
                elif score >= 40:
                    short_grade = 'D'
                    comment = 'AVERAGE'
                else:
                    short_grade = 'F'
                    comment = 'FAIL'
        else:
            score = None
            subject_position = None
            short_grade = ''
            comment = ''
        
        subjects_data.append({
            'subject': subject,
            'score': score,
            'short_grade': short_grade,
            'comment': comment,
            'position': subject_position,
            'teacher_name': grade.teacher_name if grade else '',
            'has_grade': grade is not None,
            'is_pass': grade.is_pass() if grade else False,
        })
    
    # Calculate summary statistics
    passed_count = sum(1 for s in subjects_data if s['is_pass'])
    total_subjects_with_grades = sum(1 for s in subjects_data if s['has_grade'])
    
    # Find English subject
    english_subject = next((s for s in subjects_data if s['subject'].name.lower() == 'english'), None)
    
    # Calculate overall result
    if student.is_senior:
        # For seniors: calculate total points (best 6 including English)
        senior_points = []
        for subject_data in subjects_data:
            if subject_data['has_grade'] and subject_data['score'] is not None:
                score = subject_data['score']
                if score >= 80:
                    points = 1
                elif score >= 70:
                    points = 2
                elif score >= 65:
                    points = 3
                elif score >= 60:
                    points = 4
                elif score >= 55:
                    points = 5
                elif score >= 50:
                    points = 6
                elif score >= 45:
                    points = 7
                elif score >= 40:
                    points = 8
                else:
                    points = 9
                senior_points.append(points)
        
        if english_subject and english_subject['has_grade'] and len(senior_points) >= 6:
            # Get English points
            english_score = english_subject['score']
            if english_score >= 80:
                english_points = 1
            elif english_score >= 70:
                english_points = 2
            elif english_score >= 65:
                english_points = 3
            elif english_score >= 60:
                english_points = 4
            elif english_score >= 55:
                english_points = 5
            elif english_score >= 50:
                english_points = 6
            elif english_score >= 45:
                english_points = 7
            elif english_score >= 40:
                english_points = 8
            else:
                english_points = 9
            
            # Get points for non-English subjects and sort (lower is better)
            other_points = [p for i, p in enumerate(senior_points) 
                          if subjects_data[i]['subject'].name.lower() != 'english']
            other_points.sort()
            
            # English points + best 5 other points
            total_points = english_points + sum(other_points[:5])
            
            overall_result = 'PASS' if (passed_count >= 6 and english_subject['is_pass']) else 'FAIL'
        else:
            total_points = None
            overall_result = 'FAIL - Insufficient subjects'
    else:
        # For juniors
        total_points = None
        overall_result = 'PASS' if (passed_count >= 6 and english_subject and english_subject['is_pass']) else 'FAIL'
    
    # Calculate overall position in form
    overall_position = None
    students_in_form = Student.objects.filter(form=student.form)
    student_averages = []
    
    for s in students_in_form:
        avg = s.grades.filter(term=term).aggregate(avg_score=Avg('score'))['avg_score']
        if avg is None:
            continue
        student_averages.append({
            'student': s,
            'average': float(avg)
        })
    
    # Sort by average (descending - higher is better)
    student_averages.sort(key=lambda x: x['average'], reverse=True)
    
    # Find this student's position
    for i, item in enumerate(student_averages):
        if item['student'].id == student.id:
            overall_position = i + 1
            break
    
    # Get total students in form
    total_students_in_form = students_in_form.count()

    return render(request, 'grades/student_grades.html', {
        'student': student,
        'grades': subjects_data,  # Changed from grades to subjects_data
        'passed_count': passed_count,
        'total_points': total_points,
        'overall_result': overall_result,
        'term': term,
        'overall_position': overall_position,
        'term_display': term_display,
        'total_students_in_form': total_students_in_form,
    })


@login_required
def student_profile(request):
    """View student profile."""
    student = _get_logged_student(request)
    if not student:
        return redirect('grades:student_login')
    return render(request, 'grades/student_profile.html', {'student': student})


@login_required
def report_card(request):
    """Generate the official report card matching the PDF format."""
    student = _get_logged_student(request)
    if not student:
        return redirect('grades:student_login')
    
    term = request.GET.get('term', 'T1')
    term_display = {'T1': 'Term 1', 'T2': 'Term 2', 'T3': 'Term 3'}.get(term, term)
    
    # Get all standard subjects for the report card
    standard_subjects = [
        'Agriculture', 'Bible Knowledge', 'Biology', 'Chemistry', 
        'Chichewa', 'English', 'Geography', 'History', 
        'Mathematics', 'Physics', 'Social & Life Skills'
    ]
    
    # Get or create subject records
    subjects_data = []
    for subject_name in standard_subjects:
        subject, created = Subject.objects.get_or_create(name=subject_name)
        
        # Try to get grade for this student and subject
        grade = Grade.objects.filter(
            student=student, 
            subject=subject,
            term=term
        ).first()
        
        if grade:
            score = float(grade.score)
            # Calculate position in this subject
            subject_position = Grade.objects.filter(
                subject=subject,
                term=term,
                student__form=student.form,
                score__gt=grade.score
            ).count() + 1
        else:
            score = None
            subject_position = None
            grade = None
        
        # Determine grade display based on student level
        if grade and score is not None:
            if student.is_senior:
                # Senior (Form 3-4): MSCE grading
                if score >= 80:
                    grade_display = '1'
                    remarks = 'Distinction'
                elif score >= 70:
                    grade_display = '2'
                    remarks = 'Distinction'
                elif score >= 65:
                    grade_display = '3'
                    remarks = 'Strong Credit'
                elif score >= 60:
                    grade_display = '4'
                    remarks = 'Strong Credit'
                elif score >= 55:
                    grade_display = '5'
                    remarks = 'Weak Credit'
                elif score >= 50:
                    grade_display = '6'
                    remarks = 'Weak Credit'
                elif score >= 45:
                    grade_display = '7'
                    remarks = 'Pass'
                elif score >= 40:
                    grade_display = '8'
                    remarks = 'Pass'
                else:
                    grade_display = '9'
                    remarks = 'Fail'
            else:
                # Junior (Form 1-2): JCE grading
                if score >= 80:
                    grade_display = 'A'
                    remarks = 'Excellent'
                elif score >= 70:
                    grade_display = 'B'
                    remarks = 'Very Good'
                elif score >= 50:
                    grade_display = 'C'
                    remarks = 'Good'
                elif score >= 40:
                    grade_display = 'D'
                    remarks = 'Average'
                else:
                    grade_display = 'F'
                    remarks = 'Fail'
        else:
            grade_display = ''
            remarks = ''
        
        subjects_data.append({
            'name': subject_name,
            'score': score,
            'grade_display': grade_display,
            'position': subject_position,
            'remarks': remarks,
            'teacher_name': grade.teacher_name if grade else '',
            'has_grade': grade is not None
        })
    
    # Calculate totals
    total_marks = sum(s['score'] for s in subjects_data if s['score'] is not None)
    total_subjects_with_grades = sum(1 for s in subjects_data if s['has_grade'])
    
    # Get overall position in form
    overall_position = None
    students_in_form = Student.objects.filter(form=student.form)
    student_averages = []
    
    for s in students_in_form:
        avg = s.grades.filter(term=term).aggregate(avg_score=Avg('score'))['avg_score']
        if avg is None:
            continue
        student_averages.append({
            'student': s,
            'average': float(avg)
        })
    
    # Sort by average (descending - higher is better)
    student_averages.sort(key=lambda x: x['average'], reverse=True)
    
    # Find this student's position
    for i, item in enumerate(student_averages):
        if item['student'].id == student.id:
            overall_position = i + 1
            break
    
    # Get total students in form
    total_students_in_form = students_in_form.count()
    
    context = {
        'student': student,
        'subjects': subjects_data,
        'term_display': term_display,
        'overall_position': overall_position,
        'total_students_in_form': total_students_in_form,
        'total_marks': total_marks,
        'total_subjects': total_subjects_with_grades,
        'form_teacher_remarks': student.form_teacher_remarks or '',
        'head_teacher_remarks': student.head_teacher_remarks or '',
        'other_requirements': student.other_requirements or '',
    }
    
    return render(request, 'grades/report_card.html', context)


def generate_student_pdf(student, term, request=None):
    """Generate PDF for a single student (reusable function)."""
    try:
        from weasyprint import HTML
        from weasyprint.text.fonts import FontConfiguration
    except ImportError:
        print("WeasyPrint not available. Skipping PDF generation.")
        return None
    
    term_display = {'T1': 'Term 1', 'T2': 'Term 2', 'T3': 'Term 3'}.get(term, term)
    
    # Get all standard subjects for the report card
    standard_subjects = [
        'Agriculture', 'Bible Knowledge', 'Biology', 'Chemistry', 
        'Chichewa', 'English', 'Geography', 'History', 
        'Mathematics', 'Physics', 'Social & Life Skills'
    ]
    
    # Get grades for the term
    grades_data = []
    passed_count = 0
    
    for subject_name in standard_subjects:
        subject, created = Subject.objects.get_or_create(name=subject_name)
        
        # Try to get grade for this student and subject
        grade = Grade.objects.filter(
            student=student, 
            subject=subject,
            term=term
        ).first()
        
        if grade:
            score = float(grade.score)
            
            # Determine grade display based on student level
            if student.is_senior:
                # Senior (Form 3-4): MSCE grading
                if score >= 80:
                    short_grade = '1'
                    comment = 'DISTINCTION'
                elif score >= 70:
                    short_grade = '2'
                    comment = 'DISTINCTION'
                elif score >= 65:
                    short_grade = '3'
                    comment = 'STRONG CREDIT'
                elif score >= 60:
                    short_grade = '4'
                    comment = 'STRONG CREDIT'
                elif score >= 55:
                    short_grade = '5'
                    comment = 'CREDIT'
                elif score >= 50:
                    short_grade = '6'
                    comment = 'CREDIT'
                elif score >= 45:
                    short_grade = '7'
                    comment = 'PASS'
                elif score >= 40:
                    short_grade = '8'
                    comment = 'PASS'
                else:
                    short_grade = '9'
                    comment = 'FAIL'
            else:
                # Junior (Form 1-2): JCE grading
                if score >= 80:
                    short_grade = 'A'
                    comment = 'EXCELLENT'
                elif score >= 70:
                    short_grade = 'B'
                    comment = 'VERY GOOD'
                elif score >= 50:
                    short_grade = 'C'
                    comment = 'GOOD'
                elif score >= 40:
                    short_grade = 'D'
                    comment = 'AVERAGE'
                else:
                    short_grade = 'F'
                    comment = 'FAIL'
            
            if grade.is_pass():
                passed_count += 1
        else:
            score = None
            short_grade = ''
            comment = 'No grade'
        
        grades_data.append({
            'subject': subject,
            'score': score,
            'short_grade': short_grade,
            'comment': comment,
            'is_pass': grade.is_pass() if grade else False,
        })
    
    # Calculate overall position
    overall_position = None
    students_in_form = Student.objects.filter(form=student.form)
    student_averages = []
    
    for s in students_in_form:
        avg = s.grades.filter(term=term).aggregate(avg_score=Avg('score'))['avg_score']
        if avg is None:
            continue
        student_averages.append({
            'student': s,
            'average': float(avg)
        })
    
    # Sort by average (descending - higher is better)
    student_averages.sort(key=lambda x: x['average'], reverse=True)
    
    # Find this student's position
    for i, item in enumerate(student_averages):
        if item['student'].id == student.id:
            overall_position = i + 1
            break
    
    # Determine overall result
    english_passed = any(g for g in grades_data 
                        if g['subject'].name.lower() == 'english' and g['is_pass'])
    overall_result = 'PASS' if (passed_count >= 6 and english_passed) else 'FAIL'
    
    context = {
        'student': student,
        'grades': grades_data,
        'passed_count': passed_count,
        'total_subjects': len(grades_data),
        'overall_position': overall_position,
        'overall_result': overall_result,
        'term': term,
        'term_display': term_display,
        'current_date': timezone.now().strftime("%B %d, %Y"),
    }
    
    try:
        # Render the PDF template
        html_string = render_to_string('grades/report_pdf.html', context)
        
        # Generate PDF
        font_config = FontConfiguration()
        html = HTML(string=html_string)
        pdf_bytes = html.write_pdf(font_config=font_config)
        
        return pdf_bytes
        
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        return None


@login_required
def download_report_pdf(request):
    """Generate PDF using WeasyPrint."""
    student = _get_logged_student(request)
    if not student:
        return redirect('grades:student_login')
    
    # Get term
    term = request.GET.get('term', 'T1')
    
    try:
        pdf_bytes = generate_student_pdf(student, term, request)
        
        if pdf_bytes:
            # Return PDF response
            term_display = {'T1': 'Term1', 'T2': 'Term2', 'T3': 'Term3'}.get(term, term)
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            filename = f"Report_{student.student_id}_{term_display}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        else:
            return HttpResponse('Failed to generate PDF', status=500)
            
    except Exception as e:
        import traceback
        return HttpResponse(f'PDF Generation Error: {str(e)}<br>{traceback.format_exc()}', status=500)


def is_staff_user(user):
    """Check if user is staff (teacher or admin)."""
    return user.is_authenticated and user.is_staff


@login_required
@user_passes_test(is_staff_user)
def admin_dashboard(request):
    """Dashboard for administrators and teachers."""
    # Get statistics
    total_students = Student.objects.count()
    total_grades = Grade.objects.count()
    
    # Get recent activity
    recent_grades = Grade.objects.select_related('student', 'subject').order_by('-created_at')[:10]
    
    # Get all forms available in the system
    available_forms = Student.FORM_CHOICES
    
    context = {
        'total_students': total_students,
        'total_grades': total_grades,
        'recent_grades': recent_grades,
        'available_forms': available_forms,
        'term_choices': Grade.TERM_CHOICES,
        'is_admin_user': request.user.is_superuser,
        'is_teacher_user': request.user.is_staff and not request.user.is_superuser,
    }
    
    return render(request, 'grades/admin_dashboard.html', context)


@login_required
@user_passes_test(is_staff_user)
def bulk_download_reports(request):
    """Generate PDF reports for all students in a class with single click."""
    # Get form and term from query parameters
    form = request.GET.get('form', 'F1')
    term = request.GET.get('term', 'T1')
    
    # Check if form is valid
    if form not in [f[0] for f in Student.FORM_CHOICES]:
        return HttpResponse("Invalid form selected.", status=400)
    
    # Get all students in the selected form
    students = Student.objects.filter(form=form)
    
    if not students.exists():
        return HttpResponse("No students found in this form.", status=404)
    
    # Create a ZIP file in memory
    zip_buffer = io.BytesIO()
    term_display = {'T1': 'Term1', 'T2': 'Term2', 'T3': 'Term3'}.get(term, term)
    
    with ZipFile(zip_buffer, 'w') as zip_file:
        successful = 0
        failed = 0
        
        for student in students:
            try:
                # Generate individual PDF for each student
                pdf_content = generate_student_pdf(student, term, request)
                if pdf_content:
                    filename = f"Report_{student.student_id}_{student.last_name}_{term_display}.pdf"
                    zip_file.writestr(filename, pdf_content)
                    successful += 1
                else:
                    failed += 1
            except Exception as e:
                failed += 1
                print(f"Error generating PDF for {student}: {str(e)}")
                continue
        
        # Add a summary file
        summary = f"Report Generation Summary\n"
        summary += f"========================\n"
        summary += f"Form: {dict(Student.FORM_CHOICES).get(form, form)}\n"
        summary += f"Term: {term_display}\n"
        summary += f"Total Students: {students.count()}\n"
        summary += f"Successfully Generated: {successful}\n"
        summary += f"Failed: {failed}\n"
        summary += f"Generated on: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        zip_file.writestr("GENERATION_SUMMARY.txt", summary)
    
    # Return ZIP file
    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer, content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="Reports_Form{form}_{term_display}.zip"'
    return response


@login_required
@user_passes_test(is_staff_user)
def class_ranking_report(request):
    """Generate a class ranking report showing all students with their scores."""
    form = request.GET.get('form', 'F1')
    term = request.GET.get('term', 'T1')
    
    # Get all students in the selected form
    students = Student.objects.filter(form=form).order_by('last_name', 'first_name')
    
    if not students.exists():
        return render(request, 'grades/class_ranking.html', {
            'error': f"No students found in Form {form}",
            'form': form,
            'term': term,
            'term_display': {'T1': 'Term 1', 'T2': 'Term 2', 'T3': 'Term 3'}.get(term, term),
            'form_display': dict(Student.FORM_CHOICES).get(form, f"Form {form}"),
            'form_choices': Student.FORM_CHOICES,
            'term_choices': Grade.TERM_CHOICES,
        })
    
    # Get all standard subjects
    standard_subjects = [
        'Agriculture', 'Bible Knowledge', 'Biology', 'Chemistry', 
        'Chichewa', 'English', 'Geography', 'History', 
        'Mathematics', 'Physics', 'Social & Life Skills'
    ]
    
    # Get or create subject records
    subjects = []
    for subject_name in standard_subjects:
        subject, created = Subject.objects.get_or_create(name=subject_name)
        subjects.append(subject)
    
    # Prepare student data with rankings
    student_data = []
    
    for student in students:
        # Get all grades for this student in the selected term
        grades = Grade.objects.filter(student=student, term=term).select_related('subject')
        
        # Create a dictionary of subject->grade for this student
        grade_dict = {grade.subject: grade for grade in grades}
        
        # Calculate total/average for ranking
        if student.is_senior:
            # For seniors: calculate total points (lower is better)
            senior_points = []
            for grade in grades:
                if grade.senior_point() is not None:
                    senior_points.append(grade.senior_point())
            
            if len(senior_points) >= 6:
                senior_points.sort()
                total_score = sum(senior_points[:6])  # Best 6 points
                ranking_metric = total_score
                ranking_display = f"{total_score} pts"
            else:
                total_score = None
                ranking_metric = float('inf')  # Put at bottom
                ranking_display = "Incomplete"
        else:
            # For juniors: calculate average score (higher is better)
            if grades.exists():
                total_score = sum(float(grade.score) for grade in grades)
                avg_score = total_score / len(grades)
                ranking_metric = -avg_score  # Negative for reverse sort
                ranking_display = f"{avg_score:.1f}%"
            else:
                avg_score = None
                ranking_metric = float('-inf')  # Put at bottom
                ranking_display = "No grades"
        
        # Prepare subject scores
        subject_scores = []
        for subject in subjects:
            if subject in grade_dict:
                grade = grade_dict[subject]
                score = float(grade.score)
                passed = grade.is_pass()
                subject_scores.append({
                    'score': score,
                    'display': f"{score:.1f}",
                    'passed': passed,
                    'grade': grade.letter if not student.is_senior else str(grade.senior_point() or ''),
                    'comment': grade.grade_label().split('(')[-1].rstrip(')') if '(' in grade.grade_label() else '',
                })
            else:
                # Student didn't take this subject
                subject_scores.append({
                    'score': None,
                    'display': 'AB',
                    'passed': False,
                    'grade': 'AB',
                    'comment': 'Absent',
                })
        
        student_data.append({
            'student': student,
            'grades': grades,
            'subject_scores': subject_scores,
            'ranking_metric': ranking_metric,
            'ranking_display': ranking_display,
            'total_subjects_taken': len(grades),
            'passed_count': sum(1 for grade in grades if grade.is_pass()),
        })
    
    # Sort students by ranking metric
    if students.exists() and students.first().is_senior:
        # For seniors: lower points are better (ascending)
        student_data.sort(key=lambda x: x['ranking_metric'] if x['ranking_metric'] != float('inf') else float('inf'))
    else:
        # For juniors: higher averages are better (descending)
        student_data.sort(key=lambda x: x['ranking_metric'])
    
    # Assign positions
    for i, data in enumerate(student_data):
        data['position'] = i + 1
    
    term_display = {'T1': 'Term 1', 'T2': 'Term 2', 'T3': 'Term 3'}.get(term, term)
    form_display = dict(Student.FORM_CHOICES).get(form, f"Form {form}")
    
    context = {
        'form': form,
        'form_display': form_display,
        'term': term,
        'term_display': term_display,
        'students_data': student_data,
        'subjects': subjects,
        'total_students': len(student_data),
        'is_senior': students.first().is_senior if students.exists() else False,
        'form_choices': Student.FORM_CHOICES,
        'term_choices': Grade.TERM_CHOICES,
    }
    
    return render(request, 'grades/class_ranking.html', context)


@login_required
@user_passes_test(is_staff_user)
def download_class_ranking_pdf(request):
    """Download class ranking as PDF."""
    try:
        from weasyprint import HTML
    except ImportError:
        return HttpResponse('WeasyPrint not available for PDF generation', status=500)
    
    # Get form and term
    form = request.GET.get('form', 'F1')
    term = request.GET.get('term', 'T1')
    
    # Get all students in the selected form
    students = Student.objects.filter(form=form).order_by('last_name', 'first_name')
    
    # Get all standard subjects
    standard_subjects = [
        'Agriculture', 'Bible Knowledge', 'Biology', 'Chemistry', 
        'Chichewa', 'English', 'Geography', 'History', 
        'Mathematics', 'Physics', 'Social & Life Skills'
    ]
    
    # Get or create subject records
    subjects = []
    for subject_name in standard_subjects:
        subject, created = Subject.objects.get_or_create(name=subject_name)
        subjects.append(subject)
    
    # Prepare data for PDF
    student_data = []
    for student in students:
        grades = Grade.objects.filter(student=student, term=term).select_related('subject')
        grade_dict = {grade.subject: grade for grade in grades}
        
        subject_scores = []
        for subject in subjects:
            if subject in grade_dict:
                grade = grade_dict[subject]
                subject_scores.append({
                    'score': float(grade.score),
                    'display': f"{grade.score:.1f}",
                    'passed': grade.is_pass(),
                })
            else:
                subject_scores.append({
                    'score': None,
                    'display': 'AB',
                    'passed': False,
                })
        
        # Calculate average
        valid_grades = [g for g in grades if g.score is not None]
        avg_score = sum(float(g.score) for g in valid_grades) / len(valid_grades) if valid_grades else 0
        
        student_data.append({
            'student': student,
            'subject_scores': subject_scores,
            'avg_score': avg_score,
            'passed_count': sum(1 for g in grades if g.is_pass()),
        })
    
    # Sort by average score (highest first)
    student_data.sort(key=lambda x: x['avg_score'], reverse=True)
    
    term_display = {'T1': 'Term 1', 'T2': 'Term 2', 'T3': 'Term 3'}.get(term, term)
    form_display = dict(Student.FORM_CHOICES).get(form, f"Form {form}")
    
    # Check if senior
    is_senior = False
    if student_data:
        is_senior = student_data[0]['student'].is_senior
    
    context = {
        'form': form,
        'form_display': form_display,
        'term': term,
        'term_display': term_display,
        'students_data': student_data,
        'subjects': subjects,
        'total_students': len(student_data),
        'is_senior': is_senior,
        'generated_date': timezone.now().strftime("%B %d, %Y %H:%M"),
    }
    
    try:
        # Render PDF template
        html_string = render_to_string('grades/class_ranking_pdf.html', context)
        
        # Generate PDF
        html = HTML(string=html_string)
        pdf_bytes = html.write_pdf()
        
        # Return PDF response
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f"Class_Ranking_Form{form}_{term_display.replace(' ', '_')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except Exception as e:
        return HttpResponse(f'PDF Generation Error: {str(e)}', status=500)

