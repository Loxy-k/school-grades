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


# ========== SINGLE GradeAdmin CLASS - REMOVED DUPLICATE ==========
@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'score', 'get_grade_display', 'term', 'teacher_name')
    list_filter = ('student__form', 'subject', 'term')  # Filter by form, subject, term
    search_fields = ('student__first_name', 'student__last_name', 'student__student_id', 'subject__name')
    
    # Order students alphabetically in dropdown
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "student":
            # Get current filter from URL or request
            form_filter = request.GET.get('student__form__exact', '')
            
            # Start with all students ordered alphabetically
            queryset = Student.objects.all().order_by('last_name', 'first_name')
            
            # Apply form filter if specified
            if form_filter:
                queryset = queryset.filter(form=form_filter)
            
            kwargs["queryset"] = queryset
            
        elif db_field.name == "subject":
            # Empty subject list initially - admin adds subjects
            kwargs["queryset"] = Subject.objects.all().order_by('name')
            
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    # Customize the add form to include filtering
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        
        # Add form filter to the add form if available
        form_filter = request.GET.get('form', '')
        if form_filter and 'student' in form.base_fields:
            form.base_fields['student'].queryset = Student.objects.filter(
                form=form_filter
            ).order_by('last_name', 'first_name')
        
        return form
    
    # Enhanced search functionality
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
    
    # Change list template with custom filtering
    change_list_template = 'admin/grades/grade/change_list.html'
    
    def changelist_view(self, request, extra_context=None):
        # Add form choices to context for filtering
        extra_context = extra_context or {}
        extra_context['form_choices'] = Student.FORM_CHOICES
        return super().changelist_view(request, extra_context=extra_context)
    
    # Bulk add view functionality
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('bulk-add/', self.admin_site.admin_view(self.bulk_add_view), name='grades_grade_bulk_add'),
        ]
        return custom_urls + urls
    
    def bulk_add_view(self, request):
        """Simplified bulk add view"""
        form = request.GET.get('form', '')
        subject_id = request.GET.get('subject', '')
        term = request.GET.get('term', 'T1')
        
        context = {
            **self.admin_site.each_context(request),
            'title': 'Quick Grade Entry',
            'opts': self.model._meta,
            'subjects': Subject.objects.all().order_by('name'),
        }
        
        if form:
            students = Student.objects.filter(form=form).order_by('last_name', 'first_name')
            context['students'] = students
            context['form_name'] = dict(Student.FORM_CHOICES).get(form, form)
        
        if request.method == 'POST' and 'save' in request.POST:
            # Save grades logic here
            # Get form data from POST
            form = request.POST.get('form', '')
            term = request.POST.get('term', 'T1')
            subject_id = request.POST.get('subject', '')
            
            if subject_id:
                try:
                    subject = Subject.objects.get(id=subject_id)
                    created_count = 0
                    
                    for student in Student.objects.filter(form=form):
                        score_field = f'score_{student.id}'
                        teacher_field = f'teacher_{student.id}'
                        
                        if score_field in request.POST:
                            score = request.POST.get(score_field)
                            teacher_name = request.POST.get(teacher_field, '')
                            
                            if score:  # Only create if score is provided
                                # Create or update grade
                                Grade.objects.update_or_create(
                                    student=student,
                                    subject=subject,
                                    term=term,
                                    defaults={
                                        'score': score,
                                        'teacher_name': teacher_name
                                    }
                                )
                                created_count += 1
                    
                    messages.success(request, f'Successfully saved grades for {created_count} students.')
                    return redirect('admin:grades_grade_bulk_add')
                    
                except Subject.DoesNotExist:
                    messages.error(request, 'Subject not found.')
        
        return render(request, 'admin/bulk_add_grades_simple.html', context)
