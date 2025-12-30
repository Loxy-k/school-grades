from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout, get_user_model
from .models import Student, Grade, Subject


def _get_logged_student(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return None
    try:
        return Student.objects.get(user=user)
    except Student.DoesNotExist:
        return None


def _get_total_students_in_form(student):
    """Get total number of students in the same form."""
    return Student.objects.filter(form=student.form).count()


def _calculate_position_in_form(student, term):
    """Calculate student's position in their form for a given term."""
    from django.db.models import Avg
    
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
            return i + 1
    
    return None


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
    overall_position = _calculate_position_in_form(student, term)
    total_students_in_form = _get_total_students_in_form(student)
    
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


# Update student_grades function to show simplified grading
def student_grades(request):
    student = _get_logged_student(request)
    if not student:
        return redirect('grades:student_login')
    
    term = request.GET.get('term', 'T1')
    term_display = {'T1': 'Term 1', 'T2': 'Term 2', 'T3': 'Term 3'}.get(term, term)
    
    qs = student.grades.select_related('subject').filter(term=term)
    
    grades = []
    for g in qs:
        score = float(g.score)
        
        if student.is_senior:
            # Senior grading (Forms 3-4)
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
            # Junior grading (Forms 1-2)
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
        
        # Calculate position in subject
        subject_position = Grade.objects.filter(
            subject=g.subject,
            term=term,
            student__form=student.form,
            score__gt=g.score
        ).count() + 1
        
        grades.append({
            'subject': g.subject,
            'score': score,
            'short_grade': short_grade,
            'comment': comment,
            'position': subject_position,
            'is_pass': g.is_pass(),
            'teacher_name': g.teacher_name or '',
        })
    
    # Calculate summary
    passed_count = sum(1 for g in grades if g['is_pass'])
    english_grade = next((g for g in grades if g['subject'].name.lower() == 'english'), None)
    
    if student.is_senior:
        # For seniors: calculate total points
        senior_points = []
        for g in grades:
            score = float(g['score'])
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
        
        # Sort points (lower is better) and take best 6 including English
        if english_grade and len(senior_points) >= 6:
            # Get points for non-English subjects
            other_points = [p for g, p in zip(grades, senior_points) if g['subject'].name.lower() != 'english']
            other_points.sort()  # Ascending: lower is better
            
            # English points + best 5 other points
            english_index = next(i for i, g in enumerate(grades) if g['subject'].name.lower() == 'english')
            english_points = senior_points[english_index]
            total_points = english_points + sum(other_points[:5])
            
            overall_result = 'PASS' if (passed_count >= 6 and english_grade['is_pass']) else 'FAIL'
        else:
            total_points = None
            overall_result = 'FAIL - Insufficient subjects'
    else:
        # For juniors: just check pass count
        total_points = None
        overall_result = 'PASS' if (passed_count >= 6 and english_grade and english_grade['is_pass']) else 'FAIL'
    
    # Calculate overall position
    overall_position = _calculate_position_in_form(student, term)
    
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
