# test_urls.py
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_grades.settings')

try:
    import django
    django.setup()
    
    print("Testing URL configuration...")
    
    # Try to import URLs
    from django.urls import get_resolver
    resolver = get_resolver()
    
    # List all URLs
    url_patterns = []
    try:
        for pattern in resolver.url_patterns:
            url_patterns.append(str(pattern))
    except:
        pass
    
    print(f"✅ Found {len(url_patterns)} URL patterns")
    
    if url_patterns:
        print("URL patterns found:")
        for url in url_patterns[:5]:  # Show first 5
            print(f"  - {url}")
        if len(url_patterns) > 5:
            print(f"  ... and {len(url_patterns)-5} more")
    else:
        print("⚠️ No URL patterns found!")
        
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
