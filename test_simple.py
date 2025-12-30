
# test_simple.py
import os
print("Testing if Django can start...")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_grades.settings')

try:
    import django
    django.setup()
    print("✅ Django setup successful!")
    
    # Try to create a simple response
    from django.http import HttpResponse
    response = HttpResponse("Hello World")
    print(f"✅ Created HTTP response: {response.status_code}")
    
    print("✅ Basic Django test PASSED!")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()# test_simple.py
import os
print("Testing if Django can start...")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_grades.settings')

try:
    import django
    django.setup()
    print("✅ Django setup successful!")
    
    # Try to create a simple response
    from django.http import HttpResponse
    response = HttpResponse("Hello World")
    print(f"✅ Created HTTP response: {response.status_code}")
    
    print("✅ Basic Django test PASSED!")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()# test_simple.py
import os
print("Testing if Django can start...")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_grades.settings')

try:
    import django
    django.setup()
    print("✅ Django setup successful!")
    
    # Try to create a simple response
    from django.http import HttpResponse
    response = HttpResponse("Hello World")
    print(f"✅ Created HTTP response: {response.status_code}")
    
    print("✅ Basic Django test PASSED!")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
