# grades/context_processors.py
from django.contrib.auth.models import AnonymousUser
from django.conf import settings
from .models import Student

def school_context(request):
    """Add school information, logo, and user info to all templates."""
    context = {}
    
    # ==================== SCHOOL INFORMATION ====================
    context['school'] = {
        'name': 'Fortune Seekers Private Secondary School',
        'motto': 'Where Knowledge Grows Like a Mustard Seed!',
        'tagline': 'Seek nowhere, Fortune Seekers is real!',
        'phones': ['(+265)(0)999-367-377', '(+265)(0)882-422-368'],
        'email': 'fortune.seekers@yahoo.com',
        'address': 'P. O. Box 642, Blantyre, Malawi',
        'vision': 'We strive to prepare our students to become achievers and responsible citizens ready to take future challenges head on and find solutions to them.',
        'mission': 'Our mission statement is to impart knowledge to the students with practical educational opportunities through termly comprehensive curricular and co-curricular activities using the well designed programs and contemporary learning experiences to bring our students closer to modern world.',
        'logo_path': 'grades/images/Fortune Seekers LOGO.png',
    }
    
    # Logo URL for easy access
    context['logo_url'] = f"/static/{context['school']['logo_path']}"
    
    # ==================== CURRENT YEAR ====================
    import datetime
    context['current_year'] = datetime.datetime.now().year
    
    # ==================== USER INFORMATION ====================
    if request.user.is_authenticated and not isinstance(request.user, AnonymousUser):
        try:
            # Try to get student info - FIXED: Added proper error handling
            student = Student.objects.get(user=request.user)
            
            # Build student info with safe attribute access
            student_info = {
                'is_student_user': True,
                'student_full_name': f"{student.first_name} {student.last_name}",
                'student_id': student.student_id,
                'student_form': student.form,
                'student_form_display': getattr(student, 'get_form_display', lambda: student.form)(),
                'is_senior_student': getattr(student, 'is_senior', False),
                'student_level': getattr(student, 'level', 'Unknown'),
            }
            
            # Only add optional fields if they exist
            optional_fields = ['form_teacher_remarks', 'head_teacher_remarks', 'stream']
            for field in optional_fields:
                if hasattr(student, field):
                    student_info[field] = getattr(student, field)
            
            context.update(student_info)
            
        except Student.DoesNotExist:
            # User is not a student - check if staff/admin
            if request.user.is_staff:
                context.update({
                    'is_student_user': False,
                    'is_teacher_user': not request.user.is_superuser,
                    'is_admin_user': request.user.is_superuser,
                    'user_role': 'Administrator' if request.user.is_superuser else 'Teacher',
                })
            else:
                # Regular authenticated user
                context.update({
                    'is_student_user': False,
                    'is_teacher_user': False,
                    'is_admin_user': False,
                    'user_role': 'User',
                })
        except Exception as e:
            # Catch any database errors (like missing columns)
            print(f"⚠️ Warning in context processor: {e}")
            context.update({
                'is_student_user': False,
                'is_teacher_user': False,
                'is_admin_user': False,
                'user_role': 'Error Loading',
            })
    else:
        # Anonymous user
        context.update({
            'is_student_user': False,
            'is_teacher_user': False,
            'is_admin_user': False,
            'user_role': 'Guest',
        })
    
    # ==================== FORM OPTIONS FOR TEMPLATES ====================
    context['form_choices'] = [
        ('F1', 'Form 1'),
        ('F2', 'Form 2'),
        ('F3', 'Form 3'),
        ('F4', 'Form 4'),
    ]
    
    # ==================== TERM OPTIONS ====================
    context['term_choices'] = [
        ('T1', 'Term 1'),
        ('T2', 'Term 2'),
        ('T3', 'Term 3'),
    ]
    
    # ==================== GRADING SYSTEMS INFO ====================
    context['grading_systems'] = {
        'junior': {
            'name': 'JCE (Junior Certificate of Education)',
            'forms': ['Form 1', 'Form 2'],
            'grades': {
                'A': {'range': '80-100%', 'remark': 'Excellent'},
                'B': {'range': '70-79%', 'remark': 'Very Good'},
                'C': {'range': '50-69%', 'remark': 'Good'},
                'D': {'range': '40-49%', 'remark': 'Average'},
                'F': {'range': '0-39%', 'remark': 'Fail'},
            }
        },
        'senior': {
            'name': 'MSCE (Malawi School Certificate of Education)',
            'forms': ['Form 3', 'Form 4'],
            'grades': {
                1: {'range': '80-100%', 'remark': 'Distinction'},
                2: {'range': '70-79%', 'remark': 'Distinction'},
                3: {'range': '65-69%', 'remark': 'Strong Credit'},
                4: {'range': '60-64%', 'remark': 'Strong Credit'},
                5: {'range': '55-59%', 'remark': 'Weak Credit'},  # FIXED: Added missing quote
                6: {'range': '50-54%', 'remark': 'Weak Credit'},
                7: {'range': '45-49%', 'remark': 'Pass'},
                8: {'range': '40-44%', 'remark': 'Pass'},
                9: {'range': '0-39%', 'remark': 'Fail'},
            }
        }
    }
    
    # ==================== STANDARD SUBJECTS ====================
    context['standard_subjects'] = [
        'Agriculture',
        'Bible Knowledge',
        'Biology',
        'Chemistry',
        'Chichewa',
        'English',
        'Geography',
        'History',
        'Mathematics',
        'Physics',
        'Social & Life Skills',
    ]
    
    # ==================== DEBUG INFO (only in development) ====================
    if settings.DEBUG:
        context['debug'] = {
            'user': str(request.user),
            'authenticated': request.user.is_authenticated,
            'path': request.path,
        }
    
    return context


def report_card_context(request):
    """Context processor specifically for report card pages."""
    context = {}
    
    # Add contact info specifically for report cards
    context['report_card_info'] = {
        'school_header': 'FORTUNE SEEKERS PRIVATE SECONDARY SCHOOL',
        'address': 'P. O. Box 642, Blantyre, Malawi',
        'email': 'fortune.seekers@yahoo.com',
        'phones': '(+265)(0)999-367-377 / 882-422-368',
        'motto': 'Where Knowledge Grows Like a Mustard Seed!',
        'copyright': '© FORTUNE SEEKERS PRIVATE SECONDARY SCHOOL',
        'tagline': 'Seek nowhere, Fortune Seekers is real!',
    }
    
    return context


def navigation_context(request):
    """Context processor for navigation menus."""
    context = {}
    
    # Main navigation items
    context['main_nav'] = [
        {'name': 'Home', 'url': 'grades:index', 'icon': '🏠'},
        {'name': 'Dashboard', 'url': 'grades:dashboard', 'icon': '📊', 'login_required': True},
        {'name': 'Grades', 'url': 'grades:student_grades', 'icon': '📝', 'login_required': True},
        {'name': 'Report Card', 'url': 'grades:report_card', 'icon': '📄', 'login_required': True},
        {'name': 'Profile', 'url': 'grades:student_profile', 'icon': '👤', 'login_required': True},
    ]
    
    # Admin navigation (only for staff)
    if request.user.is_authenticated and request.user.is_staff:
        context['admin_nav'] = [
            {'name': 'Admin Panel', 'url': '/admin/', 'icon': '⚙️'},
            {'name': 'Student Management', 'url': '/admin/grades/student/', 'icon': '👨‍🎓'},
            {'name': 'Grade Management', 'url': '/admin/grades/grade/', 'icon': '📊'},
        ]
    
    # Auth navigation
    if request.user.is_authenticated:
        context['auth_nav'] = [
            {'name': 'Logout', 'url': 'grades:student_logout', 'icon': '🚪'},
        ]
    else:
        context['auth_nav'] = [
            {'name': 'Student Login', 'url': 'grades:student_login', 'icon': '🔑'},
        ]
    
    return context


# Combine all context processors into one (optional)
def combined_context(request):
    """Combine all context into one dictionary."""
    context = {}
    
    try:
        # Merge all context dictionaries with error handling
        context.update(school_context(request))
        context.update(report_card_context(request))
        context.update(navigation_context(request))
    except Exception as e:
        # If context processor fails, at least return basic context
        print(f"⚠️ Error in combined_context: {e}")
        context['error'] = str(e)
    
    return context
