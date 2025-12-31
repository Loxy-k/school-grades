# grades/views.py - CLEANED UP VERSION WITH REPORTLAB ONLY
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.template.loader import render_to_string
from django.db.models import Avg
from django.urls import reverse
import os
import io
from zipfile import ZipFile

# Import your models
from .models import Student, Subject, Grade
from school_grades.settings import SCHOOL_SETTINGS


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
    term_map = {
        'T1': 'T1',
        'T2': 'T2', 
        'T3': 'T3',
        'Term 1': 'T1',
        'Term 2': 'T2',
        'Term 3': 'T3',
        'Term1': 'T1',
        'Term2': 'T2',
        'Term3': 'T3',
        'term 1': 'T1',
        'term 2': 'T2',
        'term 3': 'T3',
    }
    
    term_code = str(term_code).strip()
    if term_code in ['T1', 'T2', 'T3']:
        return term_code
    
    return term_map.get(term_code, 'T1')


def get_term_display(term_code):
    """Get display name for term."""
    term_map = {
        'T1': 'Term 1',
        'T2': 'Term 2', 
        'T3': 'Term 3',
        'Term 1': 'Term 1',
        'Term 2': 'Term 2',
        'Term 3': 'Term 3',
    }
    
    term_code = str(term_code).strip()
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
    """Student login."""
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        
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
    
    term_code = request.GET.get('term', 'T1')
    term_in_db = get_term_in_db_format(term_code)
    term_display = get_term_display(term_code)
    
    grades = Grade.objects.filter(student=student, term=term_in_db).select_related('subject')
    
    # Create a dictionary for quick lookup by subject name
    grades_by_subject = {grade.subject.name: grade for grade in grades}
    
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
            
            # Calculate position
            better_grades = Grade.objects.filter(
                subject=grade.subject, 
                term=grade.term,
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
    """Generate the official report card HTML view."""
    student = _get_logged_student(request)
    if not student:
        return redirect('grades:student_login')
    
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
        try:
            subject = Subject.objects.get(name__iexact=subject_name)
        except (Subject.DoesNotExist, Subject.MultipleObjectsReturned):
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


# ========== PDF GENERATION WITH REPORTLAB ==========
def generate_report_pdf(student, term):
    """Generate student report PDF using ReportLab with logo."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        import io
        import os
        from django.conf import settings
        
        term_display = get_term_display(term)
        term_in_db = get_term_in_db_format(term)
        
        # Get grades
        grades = Grade.objects.filter(student=student, term=term_in_db).select_related('subject')
        
        # Create PDF document
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30
        )
        
        # Content elements
        elements = []
        styles = getSampleStyleSheet()
        
        # Create custom styles
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1e3c72'),
            alignment=1,  # Center
            spaceAfter=6,
        )
        
        subheader_style = ParagraphStyle(
            'SubHeaderStyle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2a5298'),
            alignment=1,
            spaceAfter=3,
        )
        
        # Check if logo exists
        logo_path = os.path.join(settings.BASE_DIR, 'grades', 'static', 'grades', 'images', 'Fortune Seekers LOGO.png')
        logo_exists = os.path.exists(logo_path)
        # In the generate_report_pdf function, after checking logo_path:
        if os.path.exists(logo_path):
            try:
                logo = Image(logo_path, width=70, height=70)
           # Use it in header...
            except:
                # Logo exists but can't be loaded (wrong format, corrupted, etc.)
                print(f"Warning: Could not load logo from {logo_path}")
        # Continue without logo
        else:
            print(f"Logo not found at: {logo_path}")
            elements.append(Paragraph("[School Logo]", styles['Italic']))
        
        if logo_exists:
            try:
                # Header with logo on left, text on right
                header_data = [
                    [Image(logo_path, width=70, height=70), 
                     Paragraph("<b>FORTUNE SEEKERS<br/>PRIVATE SECONDARY SCHOOL</b>", header_style)]
                ]
                
                header_table = Table(header_data, colWidths=[100, 400])
                header_table.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                    ('ALIGN', (1, 0), (1, 0), 'CENTER'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ]))
                
                elements.append(header_table)
            except:
                # Fallback: Text-only header
                elements.append(Paragraph("<b>FORTUNE SEEKERS PRIVATE SECONDARY SCHOOL</b>", header_style))
        else:
            # Text-only header
            elements.append(Paragraph("<b>FORTUNE SEEKERS PRIVATE SECONDARY SCHOOL</b>", header_style))
        
        # School motto and report title
        elements.append(Paragraph('<i>"Where Knowledge Grows Like a Mustard Seed!"</i>', subheader_style))
        elements.append(Paragraph("ACADEMIC REPORT CARD", ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#dc3545'),
            alignment=1,
            spaceAfter=6,
        )))
        elements.append(Paragraph(f"{term_display} - Academic Year {SCHOOL_SETTINGS['ACADEMIC_YEAR']}", styles['Normal']))
        elements.append(Spacer(1, 15))
        
        # Student Information Table
        student_data = [
            ["Student Name:", f"{student.first_name} {student.last_name}"],
            ["Student ID:", student.student_id],
            ["Form:", student.get_form_display()],
            ["Term:", term_display],
            ["Date:", timezone.now().strftime("%B %d, %Y")],
            ["Program:", "MSCE (Senior)" if student.is_senior else "JCE (Junior)"],
        ]
        
        student_table = Table(student_data, colWidths=[100, 300])
        student_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1e3c72')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
        ]))
        
        elements.append(student_table)
        elements.append(Spacer(1, 20))
        
        # Grades Table
        if grades.exists():
            # Table header
            grades_data = [
                ["SUBJECT", "SCORE", "GRADE", "STATUS", "REMARKS"]
            ]
            
            # Add grades
            passed_count = 0
            for grade in grades:
                is_pass = grade.is_pass()
                if is_pass:
                    passed_count += 1
                
                grades_data.append([
                    grade.subject.name,
                    f"{float(grade.score):.1f}",
                    grade.get_grade_display(),
                    "PASS" if is_pass else "FAIL",
                    grade.grade_label().split('(')[-1].rstrip(')') if '(' in grade.grade_label() else '',
                ])
            
            grades_table = Table(grades_data, colWidths=[150, 60, 60, 60, 120])
            grades_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3c72')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
            ]))
            
            elements.append(grades_table)
            elements.append(Spacer(1, 15))
            
            # Summary
            summary_data = [
                ["Total Subjects", f"{len(grades)}"],
                ["Subjects Passed", f"{passed_count}"],
                ["Pass Rate", f"{(passed_count/len(grades)*100):.1f}%"],
                ["Overall Result", "PASS" if passed_count >= len(grades)/2 else "FAIL"],
            ]
            
            summary_table = Table(summary_data, colWidths=[100, 100])
            summary_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8f9fa')),
            ]))
            
            elements.append(summary_table)
        else:
            elements.append(Paragraph("No grades recorded for this term.", styles['Normal']))
        
        elements.append(Spacer(1, 20))
        
        # Remarks Section
        if student.form_teacher_remarks or student.head_teacher_remarks:
            elements.append(Paragraph("<b>REMARKS</b>", styles['Heading3']))
            if student.form_teacher_remarks:
                elements.append(Paragraph(f"<b>Form Teacher:</b> {student.form_teacher_remarks}", styles['Normal']))
            if student.head_teacher_remarks:
                elements.append(Paragraph(f"<b>Head Teacher:</b> {student.head_teacher_remarks}", styles['Normal']))
        
        elements.append(Spacer(1, 30))
        
        # Signatures
        signature_data = [
            ["_______________________", "_______________________", "_______________________"],
            ["Form Teacher", "Head Teacher", "Principal"]
        ]
        
        signature_table = Table(signature_data, colWidths=[150, 150, 150])
        signature_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        elements.append(signature_table)
        
        # Footer
        elements.append(Spacer(1, 20))
        elements.append(Paragraph(
            f"{SCHOOL_SETTINGS['ADDRESS']} | Tel: {', '.join(SCHOOL_SETTINGS['CONTACT_PHONES'])}",
            styles['Normal']
        ))
        elements.append(Paragraph(
            f"Official Document • Generated on {timezone.now().strftime('%B %d, %Y %H:%M')}",
            styles['Italic']
        ))
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
        
    except ImportError:
        print("ReportLab not installed")
        return None
    except Exception as e:
        print(f"ReportLab PDF error: {e}")
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
    
    pdf_bytes = generate_report_pdf(student, term_code)
    
    if pdf_bytes:
        term_display = get_term_display(term_code)
        term_filename = term_display.replace(' ', '')
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f"Report_{student.student_id}_{term_filename}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    else:
        messages.warning(request, 'PDF generation failed. Please use the print button instead.')
        return redirect(f'{reverse("grades:report_card")}?term={term_code}')


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
    
    # Get standard subjects
    standard_subjects = [
        'Agriculture', 'Bible Knowledge', 'Biology', 'Chemistry', 
        'Chichewa', 'English', 'Geography', 'History', 
        'Mathematics', 'Physics', 'Social & Life Skills'
    ]
    
    # Get subject objects
    subjects = []
    for subject_name in standard_subjects:
        try:
            subject = Subject.objects.get(name__iexact=subject_name)
            subjects.append(subject)
        except (Subject.DoesNotExist, Subject.MultipleObjectsReturned):
            subject = Subject.objects.create(name=subject_name, available_for='ALL')
            subjects.append(subject)
    
    # Prepare student data
    students_data = []
    all_scores_by_subject = {subject.name: [] for subject in subjects}
    
    for student in students:
        student_grades = {}
        total_score = 0
        subjects_with_grades = 0
        passed_subjects = 0
        
        # Get grades for each subject
        subject_scores = []
        for subject in subjects:
            grade = Grade.objects.filter(
                student=student, 
                subject=subject, 
                term=term_in_db
            ).first()
            
            if grade:
                score = float(grade.score)
                total_score += score
                subjects_with_grades += 1
                is_pass = grade.is_pass()
                
                if is_pass:
                    passed_subjects += 1
                
                subject_scores.append({
                    'subject': subject.name,
                    'subject_short': subject.name[:3].upper() if len(subject.name) >= 3 else subject.name.upper(),
                    'score': score,
                    'is_pass': is_pass,
                    'grade_display': grade.get_grade_display(),
                    'grade_obj': grade,
                })
                
                # Add to all scores for statistics
                all_scores_by_subject[subject.name].append({
                    'score': score,
                    'is_pass': is_pass,
                    'student_id': student.student_id
                })
            else:
                # No grade for this subject
                subject_scores.append({
                    'subject': subject.name,
                    'subject_short': subject.name[:3].upper() if len(subject.name) >= 3 else subject.name.upper(),
                    'score': None,
                    'is_pass': None,
                    'grade_display': '',
                    'grade_obj': None,
                })
        
        # Calculate average score
        avg_score = total_score / subjects_with_grades if subjects_with_grades > 0 else 0
        
        # Determine if student passed overall
        total_subjects_taken = subjects_with_grades
        passing_percentage = (passed_subjects / total_subjects_taken * 100) if total_subjects_taken > 0 else 0
        overall_pass = passing_percentage >= 50
        
        students_data.append({
            'student': student,
            'subject_scores': subject_scores,
            'avg_score': avg_score,
            'total_score': total_score,
            'passed_subjects': passed_subjects,
            'failed_subjects': subjects_with_grades - passed_subjects,
            'total_subjects_taken': total_subjects_taken,
            'passing_percentage': passing_percentage,
            'overall_pass': overall_pass,
            'comment': 'PASS' if overall_pass else 'FAIL',
        })
    
    # Sort students by total score (highest to lowest)
    students_data.sort(key=lambda x: x['total_score'], reverse=True)
    
    # Assign positions (handle ties)
    position = 1
    for i, data in enumerate(students_data):
        if i > 0 and students_data[i]['total_score'] < students_data[i-1]['total_score']:
            position = i + 1
        data['position'] = position
    
    # Calculate class statistics
    class_stats = {
        'total_students': len(students_data),
        'passing_students': sum(1 for data in students_data if data['overall_pass']),
        'failing_students': sum(1 for data in students_data if not data['overall_pass']),
        'overall_passing_percentage': (sum(1 for data in students_data if data['overall_pass']) / len(students_data) * 100) if students_data else 0,
    }
    
    # Calculate subject-wise passing percentages
    subject_stats = []
    for subject in subjects:
        subject_name = subject.name
        scores = all_scores_by_subject[subject_name]
        
        if scores:
            valid_scores = [s for s in scores if s['score'] is not None]
            if valid_scores:
                passing_count = sum(1 for s in valid_scores if s['is_pass'])
                total_count = len(valid_scores)
                passing_percentage = (passing_count / total_count * 100) if total_count > 0 else 0
                
                subject_stats.append({
                    'name': subject.name,
                    'short_name': subject.name[:3].upper() if len(subject.name) >= 3 else subject.name.upper(),
                    'total_taken': total_count,
                    'passing_count': passing_count,
                    'passing_percentage': passing_percentage,
                    'average_score': sum(s['score'] for s in valid_scores) / total_count if total_count > 0 else 0,
                })
    
    # Sort subject stats by passing percentage (highest to lowest)
    subject_stats.sort(key=lambda x: x['passing_percentage'], reverse=True)
    
    context = {
        'form': form,
        'form_display': dict(Student.FORM_CHOICES).get(form, f"Form {form}"),
        'term': term_code,
        'term_display': term_display,
        'students_data': students_data,
        'subjects': subjects,
        'subject_stats': subject_stats,
        'class_stats': class_stats,
        'form_choices': Student.FORM_CHOICES,
        'term_choices': Grade.TERM_CHOICES,
        'is_senior': form in ['F3', 'F4'],
    }
    
    # Check if it's a print request
    if request.GET.get('print') == 'true':
        return render(request, 'grades/class_ranking_print.html', context)
    
    return render(request, 'grades/class_ranking.html', context)

@login_required
@user_passes_test(is_staff_user)
def download_class_ranking_pdf(request):
    """Download class ranking as PDF with logo and improved formatting."""
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        import io
        import os
        from django.conf import settings
        
        form = request.GET.get('form', 'F1')
        term_code = request.GET.get('term', 'T1')
        term_display = get_term_display(term_code)
        
        # Get data
        term_in_db = get_term_in_db_format(term_code)
        students = Student.objects.filter(form=form).order_by('last_name', 'first_name')
        
        if not students.exists():
            return HttpResponse("No students found.", status=404)
        
        # Get subjects
        standard_subjects = [
            'Agriculture', 'Bible Knowledge', 'Biology', 'Chemistry', 
            'Chichewa', 'English', 'Geography', 'History', 
            'Mathematics', 'Physics', 'Social & Life Skills'
        ]
        
        subjects = []
        for subject_name in standard_subjects:
            try:
                subject = Subject.objects.get(name__iexact=subject_name)
                subjects.append(subject)
            except (Subject.DoesNotExist, Subject.MultipleObjectsReturned):
                subject = Subject.objects.create(name=subject_name, available_for='ALL')
                subjects.append(subject)
        
        # Prepare student data with detailed subject scores
        students_data = []
        all_scores_by_subject = {subject.name: [] for subject in subjects}
        
        for student in students:
            subject_scores = []
            total_score = 0
            subjects_with_grades = 0
            passed_subjects = 0
            
            # Get grades for each subject
            for subject in subjects:
                grade = Grade.objects.filter(
                    student=student, 
                    subject=subject, 
                    term=term_in_db
                ).first()
                
                if grade:
                    score = float(grade.score)
                    total_score += score
                    subjects_with_grades += 1
                    is_pass = grade.is_pass()
                    
                    if is_pass:
                        passed_subjects += 1
                    
                    subject_scores.append({
                        'score': score,
                        'is_pass': is_pass,
                        'display': f"{score:.1f}",
                    })
                    
                    all_scores_by_subject[subject.name].append({
                        'score': score,
                        'is_pass': is_pass,
                    })
                else:
                    subject_scores.append({
                        'score': None,
                        'is_pass': None,
                        'display': '',  # Leave blank for subjects not taken
                    })
            
            avg_score = total_score / subjects_with_grades if subjects_with_grades > 0 else 0
            overall_pass = (passed_subjects / subjects_with_grades * 100) >= 50 if subjects_with_grades > 0 else False
            
            students_data.append({
                'student': student,
                'subject_scores': subject_scores,
                'avg_score': avg_score,
                'total_score': total_score,
                'passed_subjects': passed_subjects,
                'total_subjects_taken': subjects_with_grades,
                'overall_pass': overall_pass,
                'comment': 'PASS' if overall_pass else 'FAIL',
            })
        
        # Sort by total score (highest to lowest)
        students_data.sort(key=lambda x: x['total_score'], reverse=True)
        
        # Assign positions
        for i, data in enumerate(students_data):
            data['position'] = i + 1
        
        # Calculate statistics
        class_stats = {
            'total_students': len(students_data),
            'passing_students': sum(1 for data in students_data if data['overall_pass']),
            'failing_students': sum(1 for data in students_data if not data['overall_pass']),
            'overall_passing_percentage': (sum(1 for data in students_data if data['overall_pass']) / len(students_data) * 100) if students_data else 0,
        }
        
        # Subject stats
        subject_stats = []
        for subject in subjects:
            scores = all_scores_by_subject[subject.name]
            valid_scores = [s for s in scores if s['score'] is not None]
            
            if valid_scores:
                passing_count = sum(1 for s in valid_scores if s['is_pass'])
                total_count = len(valid_scores)
                passing_percentage = (passing_count / total_count * 100) if total_count > 0 else 0
                
                subject_stats.append({
                    'name': subject.name,
                    'short_name': subject.name[:3].upper(),
                    'total_taken': total_count,
                    'passing_count': passing_count,
                    'passing_percentage': passing_percentage,
                    'average_score': sum(s['score'] for s in valid_scores) / total_count if total_count > 0 else 0,
                })
        
        # Sort subject stats
        subject_stats.sort(key=lambda x: x['passing_percentage'], reverse=True)
        
        # Create PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=landscape(A4),
            rightMargin=20,
            leftMargin=20,
            topMargin=20,
            bottomMargin=20
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Create custom styles
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1e3c72'),
            alignment=1,  # Center
            spaceAfter=6,
        )
        
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#dc3545'),
            alignment=1,
            spaceAfter=10,
        )
        
        # Check if logo exists
        logo_path = os.path.join(settings.BASE_DIR, 'grades', 'static', 'grades', 'images', 'Fortune Seekers LOGO.png')
        logo_exists = os.path.exists(logo_path)
        
        # Create header with logo
        if logo_exists:
            try:
                # Header with logo on left, text on right
                header_data = [
                    [Image(logo_path, width=70, height=70), 
                     Paragraph("<b>FORTUNE SEEKERS<br/>PRIVATE SECONDARY SCHOOL</b>", header_style)]
                ]
                
                header_table = Table(header_data, colWidths=[100, 500])
                header_table.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                    ('ALIGN', (1, 0), (1, 0), 'CENTER'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ]))
                
                elements.append(header_table)
            except:
                # Fallback: Text-only header
                elements.append(Paragraph("<b>FORTUNE SEEKERS PRIVATE SECONDARY SCHOOL</b>", header_style))
        else:
            # Text-only header
            elements.append(Paragraph("<b>FORTUNE SEEKERS PRIVATE SECONDARY SCHOOL</b>", header_style))
        
        # School motto
        elements.append(Paragraph('<i>"Where Knowledge Grows Like a Mustard Seed!"</i>', ParagraphStyle(
            'MottoStyle',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#2a5298'),
            alignment=1,
            spaceAfter=10,
        )))
        
        # Main title - BOLD WORDS as requested
        form_display = dict(Student.FORM_CHOICES).get(form, f"Form {form}")
        elements.append(Paragraph(f"<b>END OF {term_display.upper()} EXAMINATION RESULTS FOR {form_display.upper()}</b>", title_style))
        elements.append(Paragraph(f"Academic Year: {SCHOOL_SETTINGS['ACADEMIC_YEAR']}", styles['Normal']))
        elements.append(Paragraph(f"Generated: {timezone.now().strftime('%B %d, %Y %H:%M')}", styles['Normal']))
        elements.append(Spacer(1, 15))
        
        # Class Ranking Table Header
        table_header = [
            ["Position", "Student Name", "Student ID"] + 
            [subject.name[:3].upper() for subject in subjects] + 
            ["Result"]
        ]
        
        # Prepare table data
        table_data = table_header.copy()
        
        for data in students_data:
            student = data['student']
            row = [
                str(data['position']),
                f"{student.first_name} {student.last_name}",
                student.student_id
            ]
            
            # Add subject scores (leave blank if not taken)
            for score in data['subject_scores']:
                row.append(score['display'])  # Will be blank if no grade
            
            # Add PASS/FAIL result
            row.append(data['comment'])
            
            table_data.append(row)
        
        # Calculate column widths
        num_subjects = len(subjects)
        total_width = 750  # Total available width in points
        fixed_cols_width = 150 + 200 + 100  # Position + Name + ID columns
        remaining_width = total_width - fixed_cols_width - 80  # Subtract result column width
        subject_col_width = remaining_width / num_subjects if num_subjects > 0 else 40
        
        col_widths = [50, 150, 100] + [subject_col_width] * num_subjects + [80]
        
        # Create main table
        main_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        main_table.setStyle(TableStyle([
            # Header styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3c72')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            
            # Grid and borders
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            
            # Alternate row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            
            # Position column styling
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            
            # Name column alignment
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('LEFTPADDING', (1, 1), (1, -1), 5),
            
            # Result column coloring
            ('TEXTCOLOR', (-1, 1), (-1, -1), colors.green),
            ('FONTNAME', (-1, 1), (-1, -1), 'Helvetica-Bold'),
            
            # Cell padding
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            
            # Highlight top 3 positions
            ('TEXTCOLOR', (0, 1), (0, 1), colors.yellow),  # 1st position
            ('TEXTCOLOR', (0, 2), (0, 2), colors.silver),   # 2nd position
            ('TEXTCOLOR', (0, 3), (0, 3), colors.orange),   # 3rd position
        ]))
        
        elements.append(main_table)
        elements.append(Spacer(1, 20))
        
        # Statistics Section
        elements.append(Paragraph("<b>CLASS STATISTICS</b>", styles['Heading3']))
        
        # Overall class statistics
        stats_data1 = [
            ["Total Students", f"{class_stats['total_students']}"],
            ["Students Passed", f"{class_stats['passing_students']}"],
            ["Students Failed", f"{class_stats['failing_students']}"],
            ["Overall Passing Rate", f"{class_stats['overall_passing_percentage']:.1f}%"],
        ]
        
        stats_table1 = Table(stats_data1, colWidths=[150, 100])
        stats_table1.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8f9fa')),
        ]))
        
        elements.append(stats_table1)
        elements.append(Spacer(1, 15))
        
        # Subject-wise statistics
        if subject_stats:
            elements.append(Paragraph("<b>SUBJECT-WISE PERFORMANCE</b>", styles['Heading3']))
            
            # Prepare subject stats table
            subject_stats_header = ["Subject", "Students Taken", "Passed", "Passing %", "Average Score"]
            subject_stats_data = [subject_stats_header]
            
            for stat in subject_stats:
                subject_stats_data.append([
                    stat['name'],
                    str(stat['total_taken']),
                    str(stat['passing_count']),
                    f"{stat['passing_percentage']:.1f}%",
                    f"{stat['average_score']:.1f}",
                ])
            
            subject_stats_table = Table(subject_stats_data, colWidths=[150, 80, 60, 80, 80])
            subject_stats_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2a5298')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ]))
            
            elements.append(subject_stats_table)
        
        elements.append(Spacer(1, 20))
        
        # Legend/Notes
        notes_data = [
            ["Note:", "Subjects shown with 3-letter abbreviations"],
            ["", "Blank cells indicate subject not taken/written"],
            ["", f"Passing criteria: ≥50% of subjects passed"],
            ["", f"Total subjects offered: {len(subjects)}"],
        ]
        
        notes_table = Table(notes_data, colWidths=[80, 400])
        notes_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1e3c72')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ]))
        
        elements.append(notes_table)
        
        # Footer
        elements.append(Spacer(1, 20))
        elements.append(Paragraph(
            f"{SCHOOL_SETTINGS['ADDRESS']} | Tel: {', '.join(SCHOOL_SETTINGS['CONTACT_PHONES'])}",
            styles['Normal']
        ))
        elements.append(Paragraph(
            "Academic Affairs Department • Official Examination Results",
            styles['Italic']
        ))
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        
        # Return PDF
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        filename = f"Class_Ranking_{form_display.replace(' ', '_')}_{term_display.replace(' ', '_')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        # Fallback: redirect to printable HTML version
        messages.info(request, 'Use the PRINT button on the class ranking page for best results.')
        return redirect(f'{reverse("grades:class_ranking")}?form={request.GET.get("form")}&term={request.GET.get("term")}')
@login_required
@user_passes_test(is_staff_user)
def bulk_download_reports(request):
    """Generate PDF reports for all students in a class - using ReportLab."""
    form = request.GET.get('form', 'F1')
    term_code = request.GET.get('term', 'T1')
    
    if form not in [f[0] for f in Student.FORM_CHOICES]:
        return HttpResponse("Invalid form selected.", status=400)
    
    students = Student.objects.filter(form=form)
    
    if not students.exists():
        return HttpResponse("No students found in this form.", status=404)
    
    # Create ZIP file
    zip_buffer = io.BytesIO()
    term_display = get_term_display(term_code)
    
    with ZipFile(zip_buffer, 'w') as zip_file:
        successful = 0
        
        for student in students:
            pdf_content = generate_report_pdf(student, term_code)
            if pdf_content:
                filename = f"Report_{student.student_id}_{term_code}.pdf"
                zip_file.writestr(filename, pdf_content)
                successful += 1
    
    if successful == 0:
        messages.error(request, 'Failed to generate any PDF reports.')
        return redirect('grades:admin_dashboard')
    
    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer, content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="Reports_Form{form}_{term_code}.zip"'
    return response


