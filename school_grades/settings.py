import dj_database_url
from pathlib import Path
import os
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', config('SECRET_KEY', default='your-secret-key-for-local-dev-only'))

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG', 'False') == 'true'

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '.up.railway.app']
CSRF_TRUSTED_ORIGINS = ['https://*.up.railway.app']

# Application definition
INSTALLED_APPS = [
    'grades',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'school_grades.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.static',
                'django.template.context_processors.media',
                'grades.context_processors.combined_context',  # Combined context processor
            ],
        },
    },
]

WSGI_APPLICATION = 'school_grades.wsgi.application'

# Database - FIXED: Correct logic for Railway build and runtime
DATABASE_URL = os.environ.get('DATABASE_URL')

# Database configuration
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    # Fallback for local development AND Railway build phase
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation - Simplified for school system
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 4,  # Reduced for easier student access
        }
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Blantyre'  # Malawi timezone
USE_I18N = True
USE_TZ = True

# ==================== STATIC FILES CONFIGURATION ====================
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Additional locations of static files
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'grades/static'),
    os.path.join(BASE_DIR, 'static'),
]

# Ensure the static directories exist
for static_dir in STATICFILES_DIRS:
    os.makedirs(static_dir, exist_ok=True)

# Create necessary subdirectories for organization
LOGO_DIR = os.path.join(BASE_DIR, 'grades/static/grades/images')
REPORT_DIR = os.path.join(BASE_DIR, 'grades/static/grades/reports')
CSS_DIR = os.path.join(BASE_DIR, 'grades/static/grades/css')
JS_DIR = os.path.join(BASE_DIR, 'grades/static/grades/js')

for directory in [LOGO_DIR, REPORT_DIR, CSS_DIR, JS_DIR]:
    os.makedirs(directory, exist_ok=True)

# WhiteNoise configuration for serving static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ==================== MEDIA FILES CONFIGURATION ====================
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
os.makedirs(MEDIA_ROOT, exist_ok=True)

# ==================== EMAIL CONFIGURATION ====================
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'fortune.seekers@yahoo.com'
EMAIL_HOST_USER = 'fortune.seekers@yahoo.com'

# ==================== ADMIN CUSTOMIZATION ====================
ADMIN_SITE_HEADER = "Fortune Seekers Private Secondary School Administration"
ADMIN_SITE_TITLE = "Fortune Seekers School Admin Portal"
ADMIN_INDEX_TITLE = "School Management Dashboard"

# ==================== AUTHENTICATION SETTINGS ====================
LOGIN_URL = 'grades:student_login'
LOGIN_REDIRECT_URL = 'grades:dashboard'
LOGOUT_REDIRECT_URL = 'grades:index'

# Session settings (24 hours for convenience)
SESSION_COOKIE_AGE = 86400  # 24 hours in seconds
SESSION_SAVE_EVERY_REQUEST = True

# ==================== SCHOOL-SPECIFIC SETTINGS ====================
# These settings are used by the context processor
SCHOOL_SETTINGS = {
    'NAME': 'Fortune Seekers Private Secondary School',
    'MOTTO': 'Where Knowledge Grows Like a Mustard Seed!',
    'TAGLINE': 'Seek nowhere, Fortune Seekers is real!',
    'CONTACT_PHONES': ['(+265)(0)999-367-377', '(+265)(0)882-422-368'],
    'EMAIL': 'fortune.seekers@yahoo.com',
    'ADDRESS': 'P. O. Box 642, Blantyre, Malawi',
    'LOGO_PATH': 'grades/images/Fortune Seekers LOGO.png',
    'VISION': 'We strive to prepare our students to become achievers and responsible citizens ready to take future challenges head on and find solutions to them.',
    'MISSION': 'Our mission statement is to impart knowledge to the students with practical educational opportunities through termly comprehensive curricular and co-curricular activities using the well designed programs and contemporary learning experiences to bring our students closer to modern world.',
    
    # School structure
    'JUNIOR_FORMS': ['F1', 'F2'],
    'SENIOR_FORMS': ['F3', 'F4'],
    'ALL_FORMS': ['F1', 'F2', 'F3', 'F4'],
    
    # Grading systems
    'JUNIOR_GRADING': {
        'A': {'min': 80, 'max': 100, 'remark': 'Excellent'},
        'B': {'min': 70, 'max': 79, 'remark': 'Very Good'},
        'C': {'min': 50, 'max': 69, 'remark': 'Good'},
        'D': {'min': 40, 'max': 49, 'remark': 'Average'},
        'F': {'min': 0, 'max': 39, 'remark': 'Fail'},
    },
    'SENIOR_GRADING': {
        1: {'min': 80, 'max': 100, 'remark': 'Distinction'},
        2: {'min': 70, 'max': 79, 'remark': 'Distinction'},
        3: {'min': 65, 'max': 69, 'remark': 'Strong Credit'},
        4: {'min': 60, 'max': 64, 'remark': 'Strong Credit'},
        5: {'min': 55, 'max': 59, 'remark': 'Weak Credit'},
        6: {'min': 50, 'max': 54, 'remark': 'Weak Credit'},
        7: {'min': 45, 'max': 49, 'remark': 'Pass'},
        8: {'min': 40, 'max': 44, 'remark': 'Pass'},
        9: {'min': 0, 'max': 39, 'remark': 'Fail'},
    },
    
    # Standard subjects (match the report card)
    'STANDARD_SUBJECTS': [
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
    ],
    
    # Terms
    'TERMS': {
        'T1': 'Term 1',
        'T2': 'Term 2',
        'T3': 'Term 3',
    },
    
    # Academic year
    'ACADEMIC_YEAR': '2024',
}

# ==================== SECURITY SETTINGS ====================
if not DEBUG:
    # Production security settings
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    
    # Cookie security
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    
    # HSTS settings
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    
    # Other security headers
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
    
    # Static files compression and caching
    WHITENOISE_MAX_AGE = 31536000  # 1 year cache for static files
    WHITENOISE_USE_FINDERS = False
    
else:
    # Development settings
    WHITENOISE_AUTOREFRESH = True  # Auto-refresh static files
    WHITENOISE_USE_FINDERS = True  # Use Django's finders during development
    
    # Allow easier debugging
    import logging
    logging.basicConfig(level=logging.DEBUG)

# ==================== DEFAULT AUTO FIELD ====================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==================== LOGGING CONFIGURATION ====================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'debug.log'),
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'grades': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}

# ==================== CUSTOM MODEL SETTINGS ====================
# Form choices (used in templates and models)
FORM_CHOICES = [
    ('F1', 'Form 1'),
    ('F2', 'Form 2'),
    ('F3', 'Form 3'),
    ('F4', 'Form 4'),
]

# Term choices
TERM_CHOICES = [
    ('T1', 'Term 1'),
    ('T2', 'Term 2'),
    ('T3', 'Term 3'),
]

# ==================== RAILWAY SPECIFIC SETTINGS ====================
# Railway environment variables
RAILWAY_ENVIRONMENT = os.environ.get('RAILWAY_ENVIRONMENT', 'development')
RAILWAY_GIT_COMMIT_SHA = os.environ.get('RAILWAY_GIT_COMMIT_SHA', 'local')

# ==================== APPLICATION SPECIFIC SETTINGS ====================
# Minimum passing score
JUNIOR_PASSING_SCORE = 40  # 40% for Forms 1-2
SENIOR_PASSING_POINT = 8   # Points 1-8 are passing for Forms 3-4

# Number of subjects required for promotion
REQUIRED_PASSING_SUBJECTS = 6
ENGLISH_REQUIRED = True

# Report card settings
REPORT_CARD = {
    'TITLE': 'PROGRESS REPORT',
    'FOOTER_TEXT': '*** © FORTUNE SEEKERS PRIVATE SECONDARY SCHOOL ***',
    'SIGNATURE_LINES': 3,
    'DEFAULT_REMARKS': {
        'form_teacher': 'Good progress. Keep up the good work.',
        'head_teacher': 'Promoted to next class.',
        'other_requirements': 'All fees must be cleared before next term.',
    }
}

# ==================== DEPLOYMENT CHECKS ====================
# Check if running on Railway
IS_RAILWAY = 'RAILWAY' in os.environ

# Log deployment info
if IS_RAILWAY:
    print(f"🚄 Running on Railway | Environment: {RAILWAY_ENVIRONMENT} | Commit: {RAILWAY_GIT_COMMIT_SHA[:8]}")
else:
    print(f"💻 Running locally | Debug: {DEBUG}")

# Check if logo exists
LOGO_FULL_PATH = os.path.join(LOGO_DIR, 'Fortune Seekers LOGO.png')
if os.path.exists(LOGO_FULL_PATH):
    print(f"✅ School logo found: {LOGO_FULL_PATH}")
else:
    print(f"⚠️  School logo not found. Expected at: {LOGO_FULL_PATH}")
    print("   Please place 'Fortune Seekers LOGO.png' in grades/static/grades/images/")

# ==================== CONTEXT PROCESSOR CONFIG ====================
# Note: The actual context processor is imported in the TEMPLATES section above
# This is just for reference of what's available in templates

"""
Available in all templates via combined_context:

1. School Information:
   - {{ school.name }} - School name
   - {{ school.motto }} - School motto
   - {{ school.tagline }} - School tagline
   - {{ logo_url }} - URL to school logo
   - {{ school.vision }} - School vision statement
   - {{ school.mission }} - School mission statement
   - {{ school.address }}, {{ school.email }}, {{ school.phones }}

2. User Information:
   - {{ is_student_user }} - Boolean if user is a student
   - {{ student_full_name }} - Student's full name
   - {{ student_id }} - Student ID
   - {{ student_form_display }} - Form (e.g., "Form 1")
   - {{ student_level }} - "Junior" or "Senior"
   - {{ is_senior_student }} - Boolean if student is in Form 3-4
   - {{ is_teacher_user }} - Boolean if user is a teacher
   - {{ is_admin_user }} - Boolean if user is an admin
   - {{ user_role }} - User role as string

3. Navigation:
   - {{ main_nav }} - Main navigation items
   - {{ admin_nav }} - Admin navigation (for staff)
   - {{ auth_nav }} - Authentication navigation

4. Report Card Info:
   - {{ report_card_info }} - Report card specific information

5. Other:
   - {{ current_year }} - Current year
   - {{ form_choices }} - All form choices
   - {{ term_choices }} - All term choices
   - {{ grading_systems }} - Grading system info
   - {{ standard_subjects }} - Standard subject list
"""
