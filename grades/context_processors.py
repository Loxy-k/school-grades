# grades/context_processors.py
from django.contrib.auth.models import AnonymousUser
from .models import Student, UserProfile

def student_stream_info(request):
    """Add stream information to all templates."""
    context = {}
    
    # Add basic school info
    context['school_name'] = "Fortune Seekers Secondary School"
    context['school_motto'] = "Seeking Excellence in Education"
    context['current_year'] = "2024"
    
    # Add user info if authenticated
    if request.user.is_authenticated and not isinstance(request.user, AnonymousUser):
        try:
            # Try to get student info
            student = Student.objects.get(user=request.user)
            context.update({
                'student': student,
                'student_stream': student.get_stream_display(),
                'student_form_display': student.get_form_display(),
                'is_senior_student': student.is_senior,
                'student_full_name': f"{student.first_name} {student.last_name}",
                'student_id': student.student_id,
                'is_student_user': True,
            })
        except Student.DoesNotExist:
            # User is not a student
            context['is_student_user'] = False
            
            try:
                # Check for teacher/admin profile
                profile = UserProfile.objects.get(user=request.user)
                context.update({
                    'user_profile': profile,
                    'user_role': profile.get_role_display(),
                    'is_teacher_user': profile.is_teacher,
                    'is_admin_user': profile.is_admin,
                })
            except UserProfile.DoesNotExist:
                pass
    
    return context