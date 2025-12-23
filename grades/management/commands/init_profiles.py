from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from grades.models import UserProfile

class Command(BaseCommand):
    help = 'Initialize UserProfile for all existing users'
    
    def handle(self, *args, **options):
        users = User.objects.all()
        created_count = 0
        updated_count = 0
        
        for user in users:
            # Check if user already has a profile
            try:
                profile = user.profile
                # Profile exists, update if needed
                if user.is_superuser and profile.role != 'admin':
                    profile.role = 'admin'
                    profile.save()
                    updated_count += 1
                    self.stdout.write(f'↻ Updated {user.username} to admin')
                elif user.is_staff and profile.role != 'teacher':
                    profile.role = 'teacher'
                    profile.save()
                    updated_count += 1
                    self.stdout.write(f'↻ Updated {user.username} to teacher')
            except UserProfile.DoesNotExist:
                # Create new profile
                if user.is_superuser:
                    role = 'admin'
                elif user.is_staff:
                    role = 'teacher'
                else:
                    role = 'student'
                
                UserProfile.objects.create(user=user, role=role)
                created_count += 1
                self.stdout.write(f'✓ Created profile for {user.username} ({role})')
        
        self.stdout.write(self.style.SUCCESS(
            f'\nSummary: Created {created_count} new profiles, Updated {updated_count} existing profiles'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'Total users processed: {users.count()}'
        ))