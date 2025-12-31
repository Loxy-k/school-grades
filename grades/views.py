# grades/views.py - COMPLETE FIXED VERSION WITH TERM FORMAT FIX
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


# ========== HELPER FUNCTIONS ==========
def _get_logged_student(request):
    """Helper function to get the logged-in student."""
    if request.user.is_authenticated:
        try:
            return Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return None
    return None


def get_term_in_db_format(term_code):
    """Convert URL term codes to database format."""
    # Your database stores terms as 'T1', 'T2', 'T3'
    term_map = {
        'T1': 'T1',
        'T2': 'T2', 
        'T3': 'T3',
        'Term 1': 'T1',  # Map display format to DB format
        'Term 2': 'T2',
        'Term 3': 'T3',
        'Term1': 'T1',
        'Term2': 'T2',
        'Term3': 'T3',
        'term 1': 'T1',
        'term 2': 'T2',
        'term 3': 'T3',
    }
    
    # Normalize the input
    term_code = str(term_code).strip()
    
    # If it's already in database format, return as-is
    if term_code in ['T1', 'T2', 'T3']:
        return term_code
    
    # Map from other formats to database format
    return term_map.get(term_code, 'T1')  # Default to T1

def get_term_display(term_code):
    """Get display name for term."""
    # For display, show 'Term 1', 'Term 2', 'Term 3'
    term_map = {
        'T1': 'Term 1',
        'T2': 'Term 2', 
        'T3': 'Term 3',
        'Term 1': 'Term 1',
        'Term 2': 'Term 2',
        'Term 3': 'Term 3',
    }
    
    # Normalize the input
    term_code = str(term_code).strip()
    
    # Map to display format
    return term_map.get(term_code, 'Term 1')

# ========== PUBLIC VIEWS ==========
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


# ========== STUDENT VIEWS ==========
@login_required
def dashboard(request):
    """Student dashboard."""
    student = _get_logged_student(request)
    if not student:
        messages.error(request, 'Please login as a student')
        return redirect('grades:student_login')
    
    # Use database format: 'T1' not 'Term 1'
    current_term = 'T1'  # Changed from 'Term 1' to 'T1'
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
    
    # GET THE TERM FROM URL
    term_code = request.GET.get('term', 'T1')
    
    # CONVERT TO DATABASE FORMAT
    term_in_db = get_term_in_db_format(term_code)
    term_display = get_term_display(term_code)
    
    print(f"=== DEBUG: STUDENT GRADES VIEW ===")
    print(f"Student ID: {student.student_id}")
    print(f"Form: {student.form}")
    print(f"Term from URL: '{term_code}'")
    print(f"Term in DB format: '{term_in_db}'")
    
    # Get ALL grades for this student to see what's actually in the database
    all_grades = Grade.objects.filter(student=student).select_related('subject')
    print(f"Total grades in DB: {all_grades.count()}")
    
    # Print ALL grades to see actual term values
    for grade in all_grades:
        print(f"  Grade ID {grade.id}: Subject='{grade.subject.name}', Score={grade.score}, Term='{grade.term}'")
    
    # Try to find grades with different term formats
    print(f"\nTrying to find grades with term='{term_in_db}'...")
    grades = Grade.objects.filter(student=student, term=term_in_db).select_related('subject')
    print(f"Found {grades.count()} grades with exact term match")
    
    # If no grades found, try case-insensitive search
    if grades.count() == 0:
        print("\nTrying case-insensitive search...")
        # Get all grades and filter manually
        all_student_grades = Grade.objects.filter(student=student).select_related('subject')
        for g in all_student_grades:
            if g.term.lower() == term_in_db.lower():
                print(f"  Found match: '{g.term}' matches '{term_in_db}' (case-insensitive)")
        
        # Try different term formats
        term_variations = [
            'Term 1', 'Term1', 'T1', 'term 1', 'term1',
            'Term 1 ', ' Term 1', 'TERM 1', 'TERM1'
        ]
        
        print("\nTrying different term variations:")
        for term_var in term_variations:
            test_grades = Grade.objects.filter(student=student, term=term_var)
            if test_grades.exists():
                print(f"  Found {test_grades.count()} grades with term='{term_var}'")
                for g in test_grades:
                    print(f"    - Subject: {g.subject.name}, Term: '{g.term}'")
    
    # Get grades for display (use whatever works)
    grades = Grade.objects.filter(student=student, term=term_in_db).select_related('subject')
    
    # If still no grades, try a broader search
    if grades.count() == 0:
        print("\nNo grades found with exact term match. Using ALL grades for display...")
        grades = all_grades
    
    print(f"=== END DEBUG ===\n")
    
    # Create a dictionary for quick lookup by subject name
    grades_by_subject = {grade.subject.name: grade for grade in grades}
    
    # Standard subjects list
    standard_subjects = [
        'Agriculture', 'Bible Knowledge', 'Biology', 'Chemistry', 
        'Chichewa', 'English', 'Geography', 'History', 
        'Mathematics', 'Physics', 'Social & Life Skills'
    ]
    
    subjects_data = []
    passed_count = 0
    total_score = 0
    subjects_with_grades = 0
    
    for subject_name in standard_subjects:
        grade = grades_by_subject.get(subject_name)
        
        subject_info = {
            'name': subject_name,
            'has_grade': grade is not None,
        }
        
        if grade:
            score = float(grade.score)
            is_pass = grade.is_pass()
            
            if is_pass:
                passed_count += 1
            
            total_score += score
            subjects_with_grades += 1
            
            subject_info.update({
                'score': score,
                'is_pass': is_pass,
                'grade_display': grade.get_grade_display(),
                'teacher_name': grade.teacher_name or '',
                'grade_obj': grade,
            })
            
            # Calculate position - USE term_in_db for database query
            better_grades = Grade.objects.filter(
                subject=grade.subject, 
                term=grade.term,  # Use the actual term from the grade
                student__form=student.form, 
                score__gt=grade.score
            ).count()
            subject_info['position'] = better_grades + 1
        
        subjects_data.append(subject_info)
    
    # Calculate average score
    average_score = total_score / subjects_with_grades if subjects_with_grades > 0 else 0
    
    context = {
        'student': student,
        'grades': grades,
        'subjects': subjects_data,
        'term': term_code,
        'term_display': term_display,
        'passed_count': passed_count,
        'total_subjects': subjects_with_grades,
        'has_grades': subjects_with_grades > 0,
        'average_score': average_score,
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
    
    # Get term from URL and convert to database format
    term_code = request.GET.get('term', 'T1')
    term_in_db = get_term_in_db_format(term_code)
    term_display = get_term_display(term_code)
    
    # Get all subjects
    standard_subjects = [
        'Agriculture', 'Bible Knowledge', 'Biology', 'Chemistry', 
        'Chichewa', 'English', 'Geography', 'History', 
        'Mathematics', 'Physics', 'Social & Life Skills'
    ]
    
    subjects_data = []
    for subject_name in standard_subjects:
        # SAFE: Get subject with case-insensitive lookup
        try:
            # Try exact match
            subject = Subject.objects.get(name=subject_name)
        except Subject.DoesNotExist:
            try:
                # Try case-insensitive
                subject = Subject.objects.get(name__iexact=subject_name)
            except (Subject.DoesNotExist, Subject.MultipleObjectsReturned):
                # If still not found or multiple, create new
                subject = Subject.objects.create(name=subject_name)
        
        grade = Grade.objects.filter(student=student, subject=subject, term=term_in_db).first()
        
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
        
        # Convert term to database format if needed
        if term in ['T1', 'T2', 'T3']:
            term_in_db = get_term_in_db_format(term)
            term_display = get_term_display(term)
        else:
            term_in_db = term
            term_display = term
        
        standard_subjects = [
            'Agriculture', 'Bible Knowledge', 'Biology', 'Chemistry', 
            'Chichewa', 'English', 'Geography', 'History', 
            'Mathematics', 'Physics', 'Social & Life Skills'
        ]
        
        subjects_data = []
        for subject_name in standard_subjects:
            # SAFE: Get subject with case-insensitive lookup
            try:
                # Try exact match
                subject = Subject.objects.get(name=subject_name)
            except Subject.DoesNotExist:
                try:
                    # Try case-insensitive
                    subject = Subject.objects.get(name__iexact=subject_name)
                except (Subject.DoesNotExist, Subject.MultipleObjectsReturned):
                    # If still not found or multiple, skip
                    subject = None
            
            if subject:
                grade = Grade.objects.filter(
                    student=student, 
                    subject=subject, 
                    term=term_in_db
                ).first()
            else:
                grade = None
            
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
        import traceback
        traceback.print_exc()
        return None
@login_required
def download_report_pdf(request):
    """Download student report as PDF."""
    student = _get_logged_student(request)
    if not student:
        return redirect('grades:student_login')
    
    term_code = request.GET.get('term', 'T1')
    term_in_db = get_term_in_db_format(term_code)
    
    pdf_bytes = _generate_pdf_for_student(student, term_in_db)
    
    if pdf_bytes:
        term_display = get_term_display(term_code)
        # Clean term display for filename
        term_filename = term_display.replace(' ', '')
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f"Report_{student.student_id}_{term_filename}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    else:
        messages.error(request, 'Failed to generate PDF. Please try again.')
        return redirect('grades:report_card')


# ========== ADMIN/TEACHER VIEWS ==========
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
    term_code = request.GET.get('term', 'T1')
    term_in_db = get_term_in_db_format(term_code)
    
    if form not in [f[0] for f in Student.FORM_CHOICES]:
        return HttpResponse("Invalid form selected.", status=400)
    
    students = Student.objects.filter(form=form)
    
    if not students.exists():
        return HttpResponse("No students found in this form.", status=404)
    
    # Create ZIP file
    zip_buffer = io.BytesIO()
    term_display = get_term_display(term_code)
    term_filename = term_display.replace(' ', '')
    
    with ZipFile(zip_buffer, 'w') as zip_file:
        successful = 0
        
        for student in students:
            # Pass database format to PDF generator
            pdf_content = _generate_pdf_for_student(student, term_in_db)
            if pdf_content:
                filename = f"Report_{student.student_id}_{term_filename}.pdf"
                zip_file.writestr(filename, pdf_content)
                successful += 1
    
    if successful == 0:
        return HttpResponse("Failed to generate any PDFs.", status=500)
    
    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer, content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="Reports_Form{form}_{term_filename}.zip"'
    return response


@login_required
@user_passes_test(is_staff_user)
def class_ranking_report(request):
    """Generate a class ranking report."""
    form = request.GET.get('form', 'F1')
    term_code = request.GET.get('term', 'T1')
    term_in_db = get_term_in_db_format(term_code)
    term_display = get_term_display(term_code)
    
    students = Student.objects.filter(form=form).order_by('last_name', 'first_name')
    
    if not students.exists():
        messages.error(request, f"No students found in Form {form}")
        return redirect('grades:admin_dashboard')
    
    # Prepare data - USE term_in_db for queries
    student_data = []
    for student in students:
        grades = Grade.objects.filter(student=student, term=term_in_db)
        
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
        'term': term_code,
        'term_display': term_display,
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
        term_code = request.GET.get('term', 'T1')
        term_in_db = get_term_in_db_format(term_code)
        term_display = get_term_display(term_code)
        
        students = Student.objects.filter(form=form).order_by('last_name', 'first_name')
        
        if not students.exists():
            return HttpResponse("No students found.", status=404)
        
        # Prepare data - USE term_in_db for queries
        student_data = []
        for student in students:
            grades = Grade.objects.filter(student=student, term=term_in_db)
            
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
            'term': term_code,
            'term_display': term_display,
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
        filename = f"Class_Ranking_Form{form}_{term_code}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except Exception as e:
        return HttpResponse(f'PDF Generation Error: {str(e)}', status=500)




