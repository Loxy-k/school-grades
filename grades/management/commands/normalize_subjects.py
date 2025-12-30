# grades/management/commands/normalize_subjects.py
from django.core.management.base import BaseCommand
from grades.models import Subject, Grade

class Command(BaseCommand):
    help = 'Normalize all subject names to Title Case'
    
    def handle(self, *args, **options):
        # Define proper title case mappings
        subject_mappings = {
            'AGRICULTURE': 'Agriculture',
            'BIOLOGY': 'Biology',
            'CHEMISTRY': 'Chemistry',
            'PHYSICS': 'Physics',
            'MATHEMATICS': 'Mathematics',
            'ENGLISH': 'English',
            'CHICHEWA': 'Chichewa',
            'GEOGRAPHY': 'Geography',
            'HISTORY': 'History',
            'BIBLE KNOWLEDGE': 'Bible Knowledge',
            'SOCIAL & LIFE SKILLS': 'Social & Life Skills',
            # Add any other subjects you have
        }
        
        self.stdout.write("Starting subject normalization...")
        
        # Get all subjects
        subjects = Subject.objects.all()
        total_updated = 0
        
        for subject in subjects:
            original_name = subject.name
            normalized_name = None
            
            # Check if subject name is in our mapping (uppercase)
            if original_name.upper() in subject_mappings:
                normalized_name = subject_mappings[original_name.upper()]
            # Try to find a case-insensitive match
            else:
                for key, value in subject_mappings.items():
                    if original_name.upper() == key:
                        normalized_name = value
                        break
            
            # If we found a mapping, update the subject
            if normalized_name and normalized_name != original_name:
                self.stdout.write(f"Updating: '{original_name}' -> '{normalized_name}'")
                subject.name = normalized_name
                subject.save()
                total_updated += 1
            else:
                # Try to title case it if no specific mapping
                if original_name != original_name.title():
                    normalized_name = original_name.title()
                    self.stdout.write(f"Title casing: '{original_name}' -> '{normalized_name}'")
                    subject.name = normalized_name
                    subject.save()
                    total_updated += 1
                else:
                    self.stdout.write(f"Keeping: '{original_name}' (already normalized)")
        
        self.stdout.write(self.style.SUCCESS(f"\nSuccessfully normalized {total_updated} subjects!"))
        
        # Also check and update any grades that might have inconsistent subject references
        self.stdout.write("\nChecking for grades with inconsistent subject references...")
        grades = Grade.objects.all().select_related('subject')
        for grade in grades:
            self.stdout.write(f"Grade ID {grade.id}: Subject='{grade.subject.name}'")
