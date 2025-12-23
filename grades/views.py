# grades/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import PasswordResetForm
from django.utils import timezone
from django.template.loader import render_to_string
from django.db.models import Avg, Q
import os
import io
from zipfile import ZipFile
from io import BytesIO

# Import your models
from .models import Student, Subject, Grade, UserProfile

# Set WeasyPrint DLL path at the module level
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


def home(request):
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
    return redirect('grades:home')


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
    qs = student.grades.select_related('subject').filter(term=term)

    grades = []
    for g in qs:
        score = float(g.score)
        grade_label = g.grade_label()
        
        # Determine grade details based on student level
        if not student.is_senior:
            # Junior student grading
            if score >= 80:
                short_grade = 'A'
                comment = 'EXCELLENT'
            elif score >= 70:
                short_grade = 'B'
                comment = 'VERY GOOD'
            elif score >= 60:
                short_grade = 'C'
                comment = 'GOOD'
            elif score >= 50:
                short_grade = 'D'
                comment = 'PASS'
            else:
                short_grade = 'F'
                comment = 'FAIL'
        else:
            # Senior student grading
            sp = g.senior_point()
            short_grade = str(sp) if sp is not None else ''
            if sp == 1 or sp == 2:
                comment = 'DISTINCTION'
            elif sp == 3:
                comment = 'STRONG CREDIT'
            elif sp in (4, 5, 6):
                comment = 'CREDIT'
            elif sp in (7, 8):
                comment = 'PASS'
            elif sp == 9:
                comment = 'FAIL'
            else:
                comment = ''

        grades.append({
            'grade_obj': g,
            'subject': g.subject,
            'score': score,
            'grade_label': grade_label,
            'short_grade': short_grade,
            'comment': comment,
            'senior_point': g.senior_point(),
            'is_pass': g.is_pass(),
            'created_at': g.created_at,
        })

    # Compute per-subject positions
    for item in grades:
        gobj = item['grade_obj']
        subject = gobj.subject
        
        # Get scores for this subject/form/term sorted descending
        scores_qs = Grade.objects.filter(
            subject=subject,
            term=term,
            student__form=student.form
        ).values_list('score', flat=True).distinct().order_by('-score')
        
        scores = [float(s) for s in scores_qs]
        try:
            pos = scores.index(item['score']) + 1
        except ValueError:
            pos = None
        item['position'] = pos

    # Compute overall position in class for the term
    students_in_form = Student.objects.filter(form=student.form)
    student_metrics = {}

    if student.is_senior:
        # For seniors: calculate total points (lower is better)
        for s in students_in_form:
            total_points = 0
            senior_grades = s.grades.filter(term=term)
            if senior_grades.exists():
                points = [g.senior_point() for g in senior_grades if g.senior_point() is not None]
                if len(points) >= 6:
                    points.sort()
                    total_points = sum(points[:6])  # Best 6 points
                    student_metrics[s.id] = total_points
    else:
        # For juniors: calculate average score (higher is better)
        for s in students_in_form:
            avg_result = s.grades.filter(term=term).aggregate(Avg('score'))
            if avg_result['score__avg'] is not None:
                student_metrics[s.id] = float(avg_result['score__avg'])

    # Determine rankings
    overall_position = None
    if student_metrics:
        if student.is_senior:
            # For seniors: sort by total points ascending (lower is better)
            sorted_students = sorted(student_metrics.items(), key=lambda x: x[1])
        else:
            # For juniors: sort by average score descending (higher is better)
            sorted_students = sorted(student_metrics.items(), key=lambda x: x[1], reverse=True)
        
        # Find student's position
        for idx, (stu_id, score_val) in enumerate(sorted_students, 1):
            if stu_id == student.id:
                overall_position = idx
                break

    term_display = {'T1': 'Term 1', 'T2': 'Term 2', 'T3': 'Term 3'}.get(term, term)

    # Summary calculations
    passed_count = sum(1 for g in grades if g['is_pass'])

    # Find English subject
    english = next((g for g in grades if g['subject'].name.lower() == 'english'), None)

    if student.is_senior:
        # Calculate total points for seniors
        total_points = None
        overall_result = 'Fail'
        
        if english and english['senior_point'] is not None:
            other_points = [g['senior_point'] for g in grades 
                          if g['subject'].name.lower() != 'english' 
                          and g['senior_point'] is not None]
            other_points.sort()
            needed = max(0, 6 - 1)
            selected = [english['senior_point']] + other_points[:needed]
            total_points = sum(selected)
            overall_result = 'Pass' if (passed_count >= 6 and english['is_pass']) else 'Fail'
        else:
            overall_result = 'Fail - missing English'
    else:
        total_points = None
        overall_result = 'Pass' if (passed_count >= 6 and english and english['is_pass']) else 'Fail'

    return render(request, 'grades/student_grades.html', {
        'student': student,
        'grades': grades,
        'passed_count': passed_count,
        'total_points': total_points,
        'overall_result': overall_result,
        'term': term,
        'overall_position': overall_position,
        'term_display': term_display,
    })


@login_required
def student_profile(request):
    """View student profile."""
    student = _get_logged_student(request)
    if not student:
        return redirect('grades:student_login')
    return render(request, 'grades/student_profile.html', {'student': student})


def can_print_reports(user):
    """Check if user can print bulk reports."""
    if not user.is_authenticated:
        return False
    try:
        return user.profile.can_print_reports
    except:
        return False


def generate_student_pdf(student, term, request=None):
    """Generate PDF for a single student (reusable function)."""
    from weasyprint import HTML
    from weasyprint.text.fonts import FontConfiguration
    
    term_display = {'T1': 'Term 1', 'T2': 'Term 2', 'T3': 'Term 3'}.get(term, term)
    
    # Get student grades for the term
    qs = student.grades.select_related('subject').filter(term=term)
    
    grades = []
    for g in qs:
        score = float(g.score)
        if not student.is_senior:
            # Junior grading
            if score >= 80:
                short_grade = 'A'
                comment = 'EXCELLENT'
            elif score >= 70:
                short_grade = 'B'
                comment = 'VERY GOOD'
            elif score >= 60:
                short_grade = 'C'
                comment = 'GOOD'
            elif score >= 50:
                short_grade = 'D'
                comment = 'PASS'
            else:
                short_grade = 'F'
                comment = 'FAIL'
        else:
            # Senior grading
            sp = g.senior_point()
            short_grade = str(sp) if sp is not None else ''
            if sp == 1 or sp == 2:
                comment = 'DISTINCTION'
            elif sp == 3:
                comment = 'STRONG CREDIT'
            elif sp in (4, 5, 6):
                comment = 'CREDIT'
            elif sp in (7, 8):
                comment = 'PASS'
            elif sp == 9:
                comment = 'FAIL'
            else:
                comment = ''
        
        grades.append({
            'subject': g.subject,
            'score': score,
            'short_grade': short_grade,
            'comment': comment,
            'is_pass': g.is_pass(),
        })
    
    # Calculate passed count
    passed_count = sum(1 for g in grades if g['is_pass'])
    
    # Calculate class position
    overall_position = None
    students_in_form = Student.objects.filter(form=student.form)
    
    if student.is_senior:
        # Senior position calculation
        student_scores = {}
        for s in students_in_form:
            total_points = 0
            senior_grades = s.grades.filter(term=term)
            if senior_grades.exists():
                points = [g.senior_point() for g in senior_grades if g.senior_point() is not None]
                if len(points) >= 6:
                    points.sort()
                    total_points = sum(points[:6])
                    student_scores[s.id] = total_points
        
        if student_scores:
            sorted_students = sorted(student_scores.items(), key=lambda x: x[1])
            for idx, (stu_id, score_val) in enumerate(sorted_students, 1):
                if stu_id == student.id:
                    overall_position = idx
                    break
    else:
        # Junior position calculation
        student_scores = {}
        for s in students_in_form:
            avg_result = s.grades.filter(term=term).aggregate(Avg('score'))
            if avg_result['score__avg'] is not None:
                student_scores[s.id] = float(avg_result['score__avg'])
        
        if student_scores:
            sorted_students = sorted(student_scores.items(), key=lambda x: x[1], reverse=True)
            for idx, (stu_id, score_val) in enumerate(sorted_students, 1):
                if stu_id == student.id:
                    overall_position = idx
                    break
    
    # Determine overall result
    english_passed = any(g for g in grades if g['subject'].name.lower() == 'english' and g['is_pass'])
    overall_result = 'PASS' if (passed_count >= 6 and english_passed) else 'FAIL'
    
    context = {
        'student': student,
        'grades': grades,
        'passed_count': passed_count,
        'total_subjects': len(grades),
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


@login_required
@user_passes_test(can_print_reports)
def bulk_download_reports(request):
    """Generate PDF reports for all students in a class with single click."""
    print(f"DEBUG: bulk_download_reports called with form={request.GET.get('form')}, term={request.GET.get('term')}")
    
    # Get form and term from query parameters
    form = request.GET.get('form', 'F1')
    term = request.GET.get('term', 'T1')
    
    print(f"DEBUG: Processing form={form}, term={term}")
    
    # Check if teacher is authorized for this form
    try:
        user_profile = request.user.profile
        if user_profile.is_teacher and form not in user_profile.get_responsible_forms():
            return HttpResponse("You are not authorized to print reports for this form.", status=403)
    except:
        return HttpResponse("User profile error.", status=403)
    
    # Get all students in the selected form
    students = Student.objects.filter(form=form)
    
    print(f"DEBUG: Found {students.count()} students")
    
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
        summary += f"Form: {form}\n"
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
@user_passes_test(can_print_reports)
def admin_dashboard(request):
    """Dashboard for administrators and teachers to print bulk reports."""
    try:
        user_profile = request.user.profile
    except:
        return redirect('grades:home')
    
    # Get available forms
    available_forms = get_available_forms_for_user(user_profile)
    
    # Group forms by base form for display
    grouped_forms = {}
    for form_code, form_name in available_forms:
        base_form = get_base_form(form_code)
        if base_form not in grouped_forms:
            grouped_forms[base_form] = []
        stream_display = get_stream_display(form_code)
        grouped_forms[base_form].append({
            'code': form_code,
            'name': form_name,
            'stream': stream_display,
            'is_senior': form_code in ('F3S', 'F3H', 'F4S', 'F4H')
        })
    
    # Get statistics
    total_students = Student.objects.count()
    total_grades = Grade.objects.count()
    
    # Get recent activity
    recent_grades = Grade.objects.select_related('student', 'subject').order_by('-created_at')[:10]
    
    context = {
        'user_profile': user_profile,
        'available_forms': available_forms,
        'grouped_forms': grouped_forms,
        'total_students': total_students,
        'total_grades': total_grades,
        'recent_grades': recent_grades,
        'term_choices': Grade.TERM_CHOICES,
    }
    
    return render(request, 'grades/admin_dashboard.html', context)
@login_required
@user_passes_test(can_print_reports)
def class_ranking_report(request):
    """Generate a class ranking report showing all students with their scores."""
    form = request.GET.get('form', 'F1')
    term = request.GET.get('term', 'T1')
    
    # Get stream from form code
    stream = None
    if form in ('F3S', 'F4S'):
        stream = 'SCIENCE'
    elif form in ('F3H', 'F4H'):
        stream = 'HUMANITIES'
    
    # Check authorization
    try:
        user_profile = request.user.profile
        if user_profile.is_teacher and form not in user_profile.get_responsible_forms():
            return HttpResponse("You are not authorized to view reports for this form.", status=403)
    except:
        return HttpResponse("User profile error.", status=403)
    
    # Get students - filter by stream if applicable
    if stream:
        students = Student.objects.filter(form=form, stream=stream).order_by('last_name', 'first_name')
    else:
        students = Student.objects.filter(form=form).order_by('last_name', 'first_name')
    
    # Rest of the function remains similar...
    # Get all students in the selected form
    students = Student.objects.filter(form=form).order_by('last_name', 'first_name')
    
    if not students.exists():
        return render(request, 'grades/class_ranking.html', {
            'error': f"No students found in Form {form}",
            'form': form,
            'term': term,
            'term_display': {'T1': 'Term 1', 'T2': 'Term 2', 'T3': 'Term 3'}.get(term, term),
            'form_display': dict(Student.FORM_CHOICES).get(form, f"Form {form}"),
            'student_form_choices': Student.FORM_CHOICES,
            'term_choices': Grade.TERM_CHOICES,
        })
    
    # Get all subjects for this form level
    subjects = Subject.objects.filter(
        grade__student__form=form,
        grade__term=term
    ).distinct().order_by('name')
    
    # If no subjects found, get all subjects from the system
    if not subjects.exists():
        subjects = Subject.objects.all().order_by('name')
    
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
        'student_form_choices': Student.FORM_CHOICES,
        'term_choices': Grade.TERM_CHOICES,
    }
    
    return render(request, 'grades/class_ranking.html', context)


@login_required
@user_passes_test(can_print_reports)
def download_class_ranking_pdf(request):
    """Download class ranking as PDF."""
    # Get form and term
    form = request.GET.get('form', 'F1')
    term = request.GET.get('term', 'T1')
    
    # Get all students in the selected form
    students = Student.objects.filter(form=form).order_by('last_name', 'first_name')
    
    # Get subjects
    subjects = Subject.objects.filter(
        grade__student__form=form,
        grade__term=term
    ).distinct().order_by('name')
    
    if not subjects.exists():
        subjects = Subject.objects.all().order_by('name')
    
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
        from weasyprint import HTML
        
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

def get_available_forms_for_user(user_profile):
    """Get available forms for the current user."""
    if user_profile.is_admin:
        return Student.FORM_CHOICES
    else:
        teacher_forms = user_profile.get_responsible_forms()
        return [(f[0], f[1]) for f in Student.FORM_CHOICES if f[0] in teacher_forms]

def get_students_by_form_and_stream(form, stream=None):
    """Get students filtered by form and optional stream."""
    if stream:
        return Student.objects.filter(form=form, stream=stream)
    return Student.objects.filter(form=form)

def get_stream_display(form_code):
    """Get stream display name from form code."""
    stream_map = {
        'F3S': 'Science',
        'F3H': 'Humanities',
        'F4S': 'Science',
        'F4H': 'Humanities',
    }
    return stream_map.get(form_code, '')

def get_base_form(form_code):
    """Extract base form from form code (F3S -> F3)."""
    if form_code in ('F3S', 'F3H'):
        return 'F3'
    elif form_code in ('F4S', 'F4H'):
        return 'F4'
    return form_code