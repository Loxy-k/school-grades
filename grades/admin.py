from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

# Import your models
from .models import Student, Subject, Grade

# Check if UserProfile exists in models (it should after migration)
UserProfile = None
try:
    from .models import UserProfile
except ImportError:
    # UserProfile might not exist in initial state
    pass


# Only customize User admin if UserProfile exists
if UserProfile:
    class UserProfileInline(admin.StackedInline):
        model = UserProfile
        can_delete = False
        verbose_name_plural = 'User Profile'
        max_num = 1
        min_num = 1
    
    # Create a custom UserAdmin
    class CustomUserAdmin(UserAdmin):
        inlines = [UserProfileInline]
        
        def get_role(self, obj):
            try:
                return obj.profile.get_role_display()
            except:
                return "No Role"
        get_role.short_description = 'Role'
        
        list_display = UserAdmin.list_display + ('get_role',)
        list_filter = UserAdmin.list_filter + ('profile__role',)
    
    # Register/Unregister logic
    if admin.site.is_registered(User):
        admin.site.unregister(User)
    admin.site.register(User, CustomUserAdmin)
    
    # Register UserProfile admin separately
    @admin.register(UserProfile)
    class UserProfileAdmin(admin.ModelAdmin):
        list_display = ('user', 'role', 'forms_responsible')
        list_filter = ('role',)
        search_fields = ('user__username', 'user__email', 'forms_responsible')


# Your existing admin classes - KEEP THESE AS THEY WERE
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'first_name', 'last_name', 'form', 'class_level', 'linked_user', 'assigned_password_status')
    list_filter = ('form',)
    search_fields = ('first_name', 'last_name', 'student_id')

    def get_exclude(self, request, obj=None):
        if not request.user.is_superuser:
            return ('user',)
        return None

    def get_fields(self, request, obj=None):
        fields = ['student_id', 'first_name', 'last_name', 'form']
        if request.user.is_superuser:
            fields.append('user')
        fields.append('assigned_password')
        return fields
    
    def class_level(self, obj):
        return obj.level
    class_level.short_description = 'Level'

    def linked_user(self, obj):
        return obj.user.username if obj.user else ''
    linked_user.short_description = 'User'
    
    def assigned_password_status(self, obj):
        return "✓ Set" if obj.assigned_password else "✗ Not set"
    assigned_password_status.short_description = 'Password'


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'score', 'letter', 'term', 'created_at')
    list_filter = ('subject', 'term', 'student__form')
    search_fields = ('student__first_name', 'student__last_name', 'student__student_id')