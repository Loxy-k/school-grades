from django.contrib import admin
from .models import Student, Subject, Grade
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'first_name', 'last_name', 'form', 'class_level', 'linked_user')
    list_filter = ('form',)
    search_fields = ('first_name', 'last_name', 'student_id')
    fieldsets = (
        ('Personal Information', {
            'fields': ('student_id', 'first_name', 'last_name', 'form')
        }),
        ('Login Information', {
            'fields': ('user', 'assigned_password'),
            'classes': ('collapse',),
        }),
        ('Report Card Remarks', {
            'fields': ('form_teacher_remarks', 'head_teacher_remarks', 'other_requirements'),
            'classes': ('collapse',),
        }),
    )

    def get_exclude(self, request, obj=None):
        if not request.user.is_superuser:
            return ('user', 'form_teacher_remarks', 'head_teacher_remarks', 'other_requirements')
        return None

    def get_fields(self, request, obj=None):
        fields = ['student_id', 'first_name', 'last_name', 'form']
        if request.user.is_superuser:
            fields.extend(['user', 'form_teacher_remarks', 'head_teacher_remarks', 'other_requirements'])
        fields.append('assigned_password')
        return fields
    
    def class_level(self, obj):
        return obj.level
    class_level.short_description = 'Level'

    def linked_user(self, obj):
        return obj.user.username if obj.user else ''
    linked_user.short_description = 'User'


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'available_for')
    list_filter = ('available_for',)

# admin.py - UPDATE THE GradeAdmin class
@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'score', 'get_grade_display', 'term', 'teacher_name')
    list_filter = ('subject', 'term', 'student__form')  # Added student__form filter
    search_fields = ('student__first_name', 'student__last_name', 'student__student_id', 'student__form')
    
    # Add form filter and ordering
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "student":
            # Get the current form filter from request
            form_filter = request.GET.get('student__form__exact', '')
            
            if form_filter:
                # Filter students by form
                kwargs["queryset"] = Student.objects.filter(form=form_filter).order_by('last_name', 'first_name')
            else:
                # Default ordering
                kwargs["queryset"] = Student.objects.all().order_by('last_name', 'first_name')
                
        elif db_field.name == "subject":
            # Start with empty subject list (no prior subjects)
            kwargs["queryset"] = Subject.objects.all().order_by('name')
            
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    # Add filtering by student form in the admin
    def get_list_filter(self, request):
        return ('student__form', 'subject', 'term')
    
    # Custom admin view for easier grade entry
    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        
        # Enhanced search: also search by student form
        if search_term:
            # Check if search term looks like a form (F1, F2, etc.)
            if search_term.upper() in ['F1', 'F2', 'F3', 'F4']:
                queryset |= self.model.objects.filter(student__form=search_term.upper())
            
        return queryset, use_distinct
    
    fields = ('student', 'subject', 'score', 'term', 'teacher_name')
    
    def get_grade_display(self, obj):
        return obj.get_grade_display()
    get_grade_display.short_description = 'Grade'

@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    # ... existing code ...
    
    # Add a custom admin view for bulk grade entry
    change_list_template = 'admin/grades/grade/change_list.html'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('bulk-add/', self.admin_site.admin_view(self.bulk_add_view), name='grades_grade_bulk_add'),
        ]
        return custom_urls + urls
    
    def bulk_add_view(self, request):
        """Custom view for bulk grade entry with filtering"""
        context = {
            **self.admin_site.each_context(request),
            'title': 'Bulk Add Grades',
            'opts': self.model._meta,
            'form_choices': Student.FORM_CHOICES,
            'term_choices': Grade.TERM_CHOICES,
            'subjects': Subject.objects.all().order_by('name'),
        }
        
        if request.method == 'POST':
            # Handle bulk grade creation
            form = request.POST.get('form')
            term = request.POST.get('term')
            subject_id = request.POST.get('subject')
            
            if form and term and subject_id:
                students = Student.objects.filter(form=form).order_by('last_name', 'first_name')
                context['selected_form'] = form
                context['selected_term'] = term
                context['selected_subject'] = int(subject_id)
                context['students'] = students
                
                if 'save_grades' in request.POST:
                    # Save grades
                    subject = Subject.objects.get(id=subject_id)
                    created_count = 0
                    
                    for student in students:
                        score_field = f'score_{student.id}'
                        teacher_field = f'teacher_{student.id}'
                        
                        if score_field in request.POST:
                            score = request.POST.get(score_field)
                            teacher_name = request.POST.get(teacher_field, '')
                            
                            if score:
                                # Create or update grade
                                grade, created = Grade.objects.update_or_create(
                                    student=student,
                                    subject=subject,
                                    term=term,
                                    defaults={
                                        'score': score,
                                        'teacher_name': teacher_name
                                    }
                                )
                                if created:
                                    created_count += 1
                    
                    messages.success(request, f'Successfully saved grades for {created_count} students.')
                    return redirect('admin:grades_grade_bulk_add')
        
        return render(request, 'admin/bulk_add_grades.html', context)
