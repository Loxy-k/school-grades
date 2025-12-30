# grades/views.py - CLEAN FIXED VERSION
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.template.loader import render_to_string
from django.db.models import Avg
import os
import io
from zipfile import ZipFile

# Import your models
from .models import Student, Subject, Grade


def _get_logged_student(request):
    """Helper function to get the logged-in student."""
    if request.user.is_authenticated:
        try:
            return Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return None
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
    """SIMPLE student login - FIXED VERSION."""
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        
        # Debug
        print(f"LOGIN ATTEMPT: username='{username}'")
        
        if not username or not password:
            messages.error(request, 'Please provide both username and password')
            return render(request, 'grades/student_login.html')
        
        # FIRST: Try Django authentication (for staff/admin)
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('grades:dashboard')
        
        # SECOND: Try student login by student_id
        try:
            student = Student.objects.get(student_id=username)
            
            # Check if password matches assigned_password OR student_id
            if (student.assigned_password and student.assigned_password == password) or password == student.student_id:
                # Get or create user for this student
                User = get_user_model()
                username_field = f"stu_{student.student_id}"
                
                try:
                    user = User.objects.get(username=username_field)
                except User.DoesNotExist:
                    user = User.objects.create_user(
                        username=username_field,
                        email=f'{student.student_id}@fortuneschool.edu'
                    )
                
                # Link student to user
                if not student.user:
                    student.user = user
                    student.save()
                
                # Set the password and login
                user.set_password(password)
                user.save()
                login(request, user)
                
                messages.success(request, f'Welcome {student.first_name}!')
                return redirect('grades:dashboard')
            else:
                messages.error(request, 'Invalid password')
                
        except Student.DoesNotExist:
            messages.error(request, 'Student ID not found')
        except Exception as e:
            messages.error(request, f'Login error: {str(e)}')
    
    return render(request, 'grades/student_login.html')


def student_logout(request):
    """Logout the current user."""
    logout(request)
    messages.success(request, 'You have been logged out')
    return redirect('grades:index')


@login_required
def dashboard(request):
    """Student dashboard."""
    student = _get_logged_student(request)
    if not student:
        messages.error(request, 'Please login as a student')
        return redirect('grades:student_login')
    
    # Get current term grades summary
    current_term = 'T1'
    grades = student.grades.filter(term=current_term)
    passed_count = sum(1 for grade in grades if grade.is_pass())
    
    context = {
        'student': student,
        'grades_count': grades.count(),
        'passed_count': passed_count,
        'current_term': current_term,
    }
    
    return render(request, 'grades/dashboard.html', context)


@login_required
def student_grades(request):
    """View student grades for a specific term."""
    student = _get_logged_student(request)
    if not student:
        return redirect('grades:student_login')
    
    term = request.GET.get('term', 'T1')
    term_display = {'T1': 'Term 1', 'T2': 'Term 2', 'T3': 'Term 3'}.get(term, term)
    
    # Get all subjects
    standard_subjects = [
        'Agriculture', 'Bible Knowledge', 'Biology', 'Chemistry', 
        'Chichewa', 'English', 'Geography', 'History', 
        'Mathematics', 'Physics', 'Social & Life Skills'
    ]
    
    subjects_data = []
    for subject_name in standard_subjects:
        subject, created = Subject.objects.get_or_create(name=subject_name)
        grade = Grade.objects.filter(student=student, subject=subject, term=term).first()
        
        subject_info = {
            'name': subject_name,
            'has_grade': grade is not None,
        }
        
        if grade:
            score = float(grade.score)
            subject_info.update({
                'score': score,
                'is_pass': grade.is_pass(),
                'grade_display': grade.get_grade_display(),
                'teacher_name': grade.teacher_name or '',
            })
            
            # Calculate position
            better_grades = Grade.objects.filter(
                subject=subject, term=term, student__form=student.form, score__gt=grade.score
            ).count()
            subject_info['position'] = better_grades + 1
        
        subjects_data.append(subject_info)
    
    # Calculate statistics
    passed_count = sum(1 for s in subjects_data if s.get('is_pass', False))
    total_with_grades = sum(1 for s in subjects_data if s['has_grade'])
    
    context = {
        'student': student,
        'subjects': subjects_data,
        'term': term,
        'term_display': term_display,
        'passed_count': passed_count,
        'total_subjects': total_with_grades,
    }
    
    return render(request, 'grades/student_grades.html', context)


@login_required
def student_profile(request):
    """View student profile."""
    student = _get_logged_student(request)
    if not student:
        return redirect('grades:student_login')
    
    return render(request, 'grades/student_profile.html', {'student': student})


@login_required
def report_card(request):
    """Generate the official report card."""
    student = _get_logged_student(request)
    if not student:
        return redirect('grades:student_login')
    
    term = request.GET.get('term', 'T1')
    term_display = {'T1': 'Term 1', 'T2': 'Term 2', 'T3': 'Term 3'}.get(term, term)
    
    # Get all subjects
    standard_subjects = [
        'Agriculture', 'Bible Knowledge', 'Biology', 'Chemistry', 
        'Chichewa', 'English', 'Geography', 'History', 
        'Mathematics', 'Physics', 'Social & Life Skills'
    ]
    
    subjects_data = []
    for subject_name in standard_subjects:
        subject, created = Subject.objects.get_or_create(name=subject_name)
        grade = Grade.objects.filter(student=student, subject=subject, term=term).first()
        
        subject_info = {
            'name': subject_name,
            'has_grade': grade is not None,
        }
        
        if grade:
            score = float(grade.score)
            subject_info.update({
                'score': score,
                'grade_display': grade.get_grade_display(),
                'remarks': grade.grade_label().split('(')[-1].rstrip(')') if '(' in grade.grade_label() else '',
                'teacher_name': grade.teacher_name or '',
            })
        
        subjects_data.append(subject_info)
    
    context = {
        'student': student,
        'subjects': subjects_data,
        'term_display': term_display,
        'form_teacher_remarks': student.form_teacher_remarks or '',
        'head_teacher_remarks': student.head_teacher_remarks or '',
        'other_requirements': student.other_requirements or '',
    }
    
    return render(request, 'grades/report_card.html', context)


def _generate_pdf_for_student(student, term):
    """Helper to generate PDF for a student."""
    try:
        from weasyprint import HTML
        
        # Get data for PDF
        term_display = {'T1': 'Term 1', 'T2': 'Term 2', 'T3': 'Term 3'}.get(term, term)
        
        standard_subjects = [
            'Agriculture', 'Bible Knowledge', 'Biology', 'Chemistry', 
            'Chichewa', 'English', 'Geography', 'History', 
            'Mathematics', 'Physics', 'Social & Life Skills'
        ]
        
        subjects_data = []
        for subject_name in standard_subjects:
            subject, created = Subject.objects.get_or_create(name=subject_name)
            grade = Grade.objects.filter(student=student, subject=subject, term=term).first()
            
            subject_info = {
                'name': subject_name,
                'has_grade': grade is not None,
            }
            
            if grade:
                score = float(grade.score)
                subject_info.update({
                    'score': score,
                    'grade_display': grade.get_grade_display(),
                    'remarks': grade.grade_label().split('(')[-1].rstrip(')') if '(' in grade.grade_label() else '',
                })
            
            subjects_data.append(subject_info)
        
        context = {
            'student': student,
            'subjects': subjects_data,
            'term_display': term_display,
            'current_date': timezone.now().strftime("%B %d, %Y"),
            'form_teacher_remarks': student.form_teacher_remarks or '',
            'head_teacher_remarks': student.head_teacher_remarks or '',
        }
        
        # Render HTML
        html_string = render_to_string('grades/report_pdf.html', context)
        
        # Generate PDF
        html = HTML(string=html_string)
        pdf_bytes = html.write_pdf()
        
        return pdf_bytes
        
    except ImportError:
        print("WeasyPrint not installed")
        return None
    except Exception as e:
        print(f"PDF generation error: {e}")
        return None


@login_required
def download_report_pdf(request):
    """Download student report as PDF."""
    student = _get_logged_student(request)
    if not student:
        return redirect('grades:student_login')
    
    term = request.GET.get('term', 'T1')
    
    pdf_bytes = _generate_pdf_for_student(student, term)
    
    if pdf_bytes:
        term_display = {'T1': 'Term1', 'T2': 'Term2', 'T3': 'Term3'}.get(term, term)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f"Report_{student.student_id}_{term_display}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    else:
        messages.error(request, 'Failed to generate PDF. Please try again.')
        return redirect('grades:report_card')


def is_staff_user(user):
    """Check if user is staff (teacher or admin)."""
    return user.is_authenticated and user.is_staff


@login_required
@user_passes_test(is_staff_user)
def admin_dashboard(request):
    """Dashboard for administrators and teachers."""
    context = {
        'total_students': Student.objects.count(),
        'total_grades': Grade.objects.count(),
        'available_forms': Student.FORM_CHOICES,
        'term_choices': Grade.TERM_CHOICES,
    }
    
    return render(request, 'grades/admin_dashboard.html', context)


@login_required
@user_passes_test(is_staff_user)
def bulk_download_reports(request):
    """Generate PDF reports for all students in a class."""
    form = request.GET.get('form', 'F1')
    term = request.GET.get('term', 'T1')
    
    if form not in [f[0] for f in Student.FORM_CHOICES]:
        return HttpResponse("Invalid form selected.", status=400)
    
    students = Student.objects.filter(form=form)
    
    if not students.exists():
        return HttpResponse("No students found in this form.", status=404)
    
    # Create ZIP file
    zip_buffer = io.BytesIO()
    term_display = {'T1': 'Term1', 'T2': 'Term2', 'T3': 'Term3'}.get(term, term)
    
    with ZipFile(zip_buffer, 'w') as zip_file:
        successful = 0
        
        for student in students:
            pdf_content = _generate_pdf_for_student(student, term)
            if pdf_content:
                filename = f"Report_{student.student_id}_{term_display}.pdf"
                zip_file.writestr(filename, pdf_content)
                successful += 1
    
    if successful == 0:
        return HttpResponse("Failed to generate any PDFs.", status=500)
    
    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer, content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="Reports_Form{form}_{term_display}.zip"'
    return response


@login_required
@user_passes_test(is_staff_user)
def class_ranking_report(request):
    """Generate a class ranking report."""
    form = request.GET.get('form', 'F1')
    term = request.GET.get('term', 'T1')
    
    students = Student.objects.filter(form=form).order_by('last_name', 'first_name')
    
    if not students.exists():
        messages.error(request, f"No students found in Form {form}")
        return redirect('grades:admin_dashboard')
    
    # Prepare data
    student_data = []
    for student in students:
        grades = Grade.objects.filter(student=student, term=term)
        
        if grades.exists():
            avg_score = grades.aggregate(avg=Avg('score'))['avg']
            avg_score = float(avg_score) if avg_score else 0
            passed_count = sum(1 for grade in grades if grade.is_pass())
        else:
            avg_score = 0
            passed_count = 0
        
        student_data.append({
            'student': student,
            'avg_score': avg_score,
            'passed_count': passed_count,
            'total_grades': grades.count(),
        })
    
    # Sort by average score
    student_data.sort(key=lambda x: x['avg_score'], reverse=True)
    
    # Assign positions
    for i, data in enumerate(student_data):
        data['position'] = i + 1
    
    context = {
        'form': form,
        'form_display': dict(Student.FORM_CHOICES).get(form, f"Form {form}"),
        'term': term,
        'term_display': {'T1': 'Term 1', 'T2': 'Term 2', 'T3': 'Term 3'}.get(term, term),
        'students_data': student_data,
        'total_students': len(student_data),
    }
    
    return render(request, 'grades/class_ranking.html', context)


@login_required
@user_passes_test(is_staff_user)
def download_class_ranking_pdf(request):
    """Download class ranking as PDF."""
    try:
        from weasyprint import HTML
        
        form = request.GET.get('form', 'F1')
        term = request.GET.get('term', 'T1')
        
        students = Student.objects.filter(form=form).order_by('last_name', 'first_name')
        
        if not students.exists():
            return HttpResponse("No students found.", status=404)
        
        # Prepare data
        student_data = []
        for student in students:
            grades = Grade.objects.filter(student=student, term=term)
            
            if grades.exists():
                avg_score = grades.aggregate(avg=Avg('score'))['avg']
                avg_score = float(avg_score) if avg_score else 0
            else:
                avg_score = 0
            
            student_data.append({
                'student': student,
                'avg_score': avg_score,
                'total_grades': grades.count(),
            })
        
        # Sort by average score
        student_data.sort(key=lambda x: x['avg_score'], reverse=True)
        
        context = {
            'form': form,
            'form_display': dict(Student.FORM_CHOICES).get(form, f"Form {form}"),
            'term': term,
            'term_display': {'T1': 'Term 1', 'T2': 'Term 2', 'T3': 'Term 3'}.get(term, term),
            'students_data': student_data,
            'total_students': len(student_data),
            'generated_date': timezone.now().strftime("%B %d, %Y %H:%M"),
        }
        
        # Render PDF
        html_string = render_to_string('grades/class_ranking_pdf.html', context)
        html = HTML(string=html_string)
        pdf_bytes = html.write_pdf()
        
        # Return PDF
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f"Class_Ranking_Form{form}_{term}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except Exception as e:
        return HttpResponse(f'PDF Generation Error: {str(e)}', status=500)
