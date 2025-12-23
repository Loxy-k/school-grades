from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Include grades URLs with explicit namespace so view redirects using
    # the 'grades:' prefix resolve correctly (views use 'grades:dashboard').
    path('', include(('grades.urls', 'grades'), namespace='grades')),
]
