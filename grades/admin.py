from django.contrib import admin
from .models import Student, Subject, Grade


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


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'score', 'get_grade_display', 'term', 'teacher_name')
    list_filter = ('subject', 'term')
    search_fields = ('student__first_name', 'student__last_name', 'student__student_id')
    fields = ('student', 'subject', 'score', 'term', 'teacher_name')
    
    def get_grade_display(self, obj):
        return obj.get_grade_display()
    get_grade_display.short_description = 'Grade'
