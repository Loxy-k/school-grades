#!/usr/bin/env python
# debug_startup.py - Debug Django startup

import os
import sys

print("=" * 60)
print("DJANGO STARTUP DEBUG")
print("=" * 60)

# Check critical environment variables
print("\n1. ENVIRONMENT VARIABLES:")
critical_vars = ['DATABASE_URL', 'PORT', 'DJANGO_SECRET_KEY']
for var in critical_vars:
    value = os.environ.get(var)
    if value:
        if var == 'DJANGO_SECRET_KEY':
            print(f"   {var}: ✅ SET (hidden)")
        else:
            print(f"   {var}: ✅ SET = {value[:50]}..." if len(str(value)) > 50 else f"   {var}: ✅ SET = {value}")
    else:
        print(f"   {var}: ⚠️ NOT SET")

# Try to import Django settings
print("\n2. IMPORTING DJANGO SETTINGS...")
try:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_grades.settings')
    
    import django
    django.setup()
    
    from django.conf import settings
    
    print(f"   ✅ Settings imported successfully")
    print(f"   DEBUG: {settings.DEBUG}")
    print(f"   ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
    
    # Test database connection
    from django.db import connection
    connection.ensure_connection()
    print(f"   DATABASE: ✅ CONNECTED")
    
    # Test if app can start
    print("\n3. TESTING WSGI APPLICATION...")
    from school_grades.wsgi import application
    print(f"   ✅ WSGI application loaded")
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED! ✅ READY TO START")
    print("=" * 60)
    
except Exception as e:
    print(f"\n❌ ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
