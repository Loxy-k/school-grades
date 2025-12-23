# grades/management/commands/create_user_profiles.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from grades.models import UserProfile, Student

class Command(BaseCommand):
    help = 'Create UserProfile for existing users and auto-assign roles'
    
    def handle(self, *args, **kwargs):
        # Create profiles for all users without one
        users_without_profile = User.objects.filter(profile__isnull=True)
        
        created_count = 0
        for user in users_without_profile:
            # Determine role based on existing relationships
            role = 'student'  # default
            
            # Check if user is linked to a student
            if Student.objects.filter(user=user).exists():
                role = 'student'
            # Check if user is staff (could be teacher/admin)
            elif user.is_staff:
                if user.is_superuser:
                    role = 'admin'
                else:
                    role = 'teacher'
            
            UserProfile.objects.create(user=user, role=role)
            created_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Successfully created {created_count} UserProfile(s)'))
        
        # Also update existing profiles without role
        profiles_without_role = UserProfile.objects.filter(role='student')
        updated_count = 0
        
        for profile in profiles_without_role:
            user = profile.user
            if user.is_staff:
                if user.is_superuser:
                    profile.role = 'admin'
                else:
                    profile.role = 'teacher'
                profile.save()
                updated_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Updated {updated_count} existing profile(s)'))