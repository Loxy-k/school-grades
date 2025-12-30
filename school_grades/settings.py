import os
import sys
from pathlib import Path
import dj_database_url

# ==================== DEBUG: ENVIRONMENT CHECK ====================
print("=" * 80)
print("DEBUG: CHECKING ENVIRONMENT IN SETTINGS.PY")
print("=" * 80)

# Check DATABASE_URL
db_url = os.environ.get('DATABASE_URL')
print(f"DATABASE_URL in settings.py: {'✅ FOUND' if db_url else '❌ NOT FOUND'}")
if db_url:
    print(f"Value: {db_url[:50]}...")
else:
    print("⚠️ WARNING: DATABASE_URL not found - will use SQLite")
    print("This means your data will be LOST on every deployment!")
    
# Check DJANGO_SECRET_KEY  
secret_key = os.environ.get('DJANGO_SECRET_KEY')
print(f"DJANGO_SECRET_KEY: {'✅ FOUND' if secret_key else '❌ NOT FOUND'}")

# Check DEBUG
debug_val = os.environ.get('DEBUG', 'False')
print(f"DEBUG from env: {debug_val}")

# List relevant environment variables
print("\nRelevant environment variables:")
for key, value in sorted(os.environ.items()):
    if any(k in key for k in ['DATABASE', 'SECRET', 'DEBUG', 'PORT', 'POSTGRES']):
        if 'SECRET' in key or 'KEY' in key or 'PASS' in key:
            print(f"  {key}: {'*' * 10} (hidden)")
        else:
            print(f"  {key}: {value[:100]}...")

print("=" * 80)

# ==================== BASE CONFIGURATION ====================
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ==================== SECURITY SETTINGS ====================
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-dev-key-change-this-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = ['*']  # Allow all for Railway deployment
CSRF_TRUSTED_ORIGINS = ['https://*.up.railway.app', 'https://*.railway.app']

# ==================== DATABASE CONFIGURATION ====================
print("\n🔧 CONFIGURING DATABASE...")

DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    print("✅ Using PostgreSQL from Railway...")
    try:
        DATABASES = {
            'default': dj_database_url.config(
                default=DATABASE_URL,
                conn_max_age=600,
                conn_health_checks=True,
                ssl_require=True
            )
        }
        # Force SSL for Railway PostgreSQL
        DATABASES['default']['OPTIONS'] = {
            'sslmode': 'require',
        }
        print("✅ PostgreSQL configured with SSL")
    except Exception as e:
        print(f"❌ Error configuring PostgreSQL: {e}")
        print("⚠️ Falling back to SQLite...")
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
            }
        }
else:
    print("⚠️ DATABASE_URL not found, using SQLite (data will not persist!)")
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

print(f"Database engine: {DATABASES['default']['ENGINE']}")
print("=" * 80)

# ==================== APPLICATION DEFINITION ====================
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
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Must be after SecurityMiddleware
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
                'grades.context_processors.combined_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'school_grades.wsgi.application'

# ==================== PASSWORD VALIDATION ====================
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 4,
        }
    },
]

# ==================== INTERNATIONALIZATION ====================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Blantyre'
USE_I18N = True
USE_TZ = True

# ==================== STATIC FILES CONFIGURATION ====================
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Additional locations of static files
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'grades/static'),
]

# Create necessary directories
for static_dir in STATICFILES_DIRS:
    os.makedirs(static_dir, exist_ok=True)

# Create subdirectories for organization
LOGO_DIR = os.path.join(BASE_DIR, 'grades/static/grades/images')
REPORT_DIR = os.path.join(BASE_DIR, 'grades/static/grades/reports')
CSS_DIR = os.path.join(BASE_DIR, 'grades/static/grades/css')
JS_DIR = os.path.join(BASE_DIR, 'grades/static/grades/js')

for directory in [LOGO_DIR, REPORT_DIR, CSS_DIR, JS_DIR]:
    os.makedirs(directory, exist_ok=True)

# WhiteNoise configuration
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ==================== MEDIA FILES ====================
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
os.makedirs(MEDIA_ROOT, exist_ok=True)

# ==================== EMAIL CONFIGURATION ====================
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'fortune.seekers@yahoo.com'

# ==================== ADMIN CUSTOMIZATION ====================
ADMIN_SITE_HEADER = "Fortune Seekers Private Secondary School Administration"
ADMIN_SITE_TITLE = "Fortune Seekers School Admin Portal"
ADMIN_INDEX_TITLE = "School Management Dashboard"

# ==================== AUTHENTICATION SETTINGS ====================
LOGIN_URL = 'grades:student_login'
LOGIN_REDIRECT_URL = 'grades:dashboard'
LOGOUT_REDIRECT_URL = 'grades:index'

# Session settings (24 hours)
SESSION_COOKIE_AGE = 86400
SESSION_SAVE_EVERY_REQUEST = True

# ==================== SCHOOL-SPECIFIC SETTINGS ====================
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
    
    # Standard subjects
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

# ==================== PRODUCTION SECURITY SETTINGS ====================
if not DEBUG:
    # Production security settings
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    
    # Cookie security
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    
    # HSTS settings
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    
    # Other security headers
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
    
    # Static files caching
    WHITENOISE_MAX_AGE = 31536000
    
else:
    # Development settings
    WHITENOISE_AUTOREFRESH = True

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
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'grades': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}

# ==================== CUSTOM MODEL SETTINGS ====================
FORM_CHOICES = [
    ('F1', 'Form 1'),
    ('F2', 'Form 2'),
    ('F3', 'Form 3'),
    ('F4', 'Form 4'),
]

TERM_CHOICES = [
    ('T1', 'Term 1'),
    ('T2', 'Term 2'),
    ('T3', 'Term 3'),
]

# ==================== APPLICATION SPECIFIC SETTINGS ====================
# Minimum passing scores
JUNIOR_PASSING_SCORE = 40
SENIOR_PASSING_POINT = 8

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

# ==================== FINAL STARTUP MESSAGE ====================
print("\n" + "=" * 80)
print("SCHOOL GRADES SYSTEM - SETTINGS LOADED")
print("=" * 80)
print(f"Environment: {'🚄 Railway' if 'RAILWAY' in os.environ else '💻 Local'}")
print(f"Debug Mode: {'✅ ON' if DEBUG else '❌ OFF'}")
print(f"Database: {'✅ PostgreSQL' if DATABASE_URL else '⚠️ SQLite'}")
print(f"Allowed Hosts: {ALLOWED_HOSTS}")
print("=" * 80)

# Check if logo exists
LOGO_FULL_PATH = os.path.join(LOGO_DIR, 'Fortune Seekers LOGO.png')
if os.path.exists(LOGO_FULL_PATH):
    print(f"✅ School logo found")
else:
    print(f"⚠️ School logo not found at: {LOGO_FULL_PATH}")

print("=" * 80)
print("Settings loaded successfully! Ready to start Django.")
print("=" * 80 + "\n")
# ==================== FINAL DATABASE VERIFICATION ====================
print("\n" + "=" * 80)
print("DATABASE CONFIGURATION - FINAL VERIFICATION")
print("=" * 80)

try:
    from django.db import connection
    
    # Test the connection
    connection.ensure_connection()
    
    # Get database info
    db_vendor = connection.vendor
    db_name = connection.settings_dict.get('NAME', 'Unknown')
    db_host = connection.settings_dict.get('HOST', 'Unknown')
    
    print(f"Database Vendor: {db_vendor.upper()}")
    print(f"Database Name: {db_name}")
    
    if db_vendor == 'postgresql':
        print("🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉")
        print("✅ SUCCESS: USING POSTGRESQL!")
        print("🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉")
        print("")
        print("📊 YOUR DATA IS SAFE AND WILL PERSIST!")
        print("✓ Passwords remain the same after redeploy")
        print("✓ Student grades are saved forever")
        print("✓ No need to create new admin users")
        print("✓ All data survives code updates")
        print("")
        print(f"Connected to: {db_host}")
        
        # Show PostgreSQL version
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT version();")
                version = cursor.fetchone()[0]
                print(f"PostgreSQL Version: {version.split(',')[0]}")
        except:
            pass
            
    elif db_vendor == 'sqlite':
        print("🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥")
        print("❌ WARNING: USING SQLITE!")
        print("🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥")
        print("")
        print("🚨 YOUR DATA WILL BE LOST ON EVERY DEPLOY!")
        print("✗ All passwords reset on redeploy")
        print("✗ Student grades deleted after updates")
        print("✗ Need new admin user each time")
        print("✗ Everything starts fresh like new installation")
        print("")
        print("⚠️  Check DATABASE_URL environment variable!")
        
    else:
        print(f"Database Type: {db_vendor}")
        print(f"Database: {db_name}")
        
    print("=" * 80)
    print("Database verification complete!")
    print("=" * 80)
    
except Exception as e:
    print(f"❌ Error during database verification: {e}")
    print("=" * 80)

