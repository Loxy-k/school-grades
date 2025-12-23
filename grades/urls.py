# grades/urls.py
from django.urls import path
from . import views

app_name = 'grades'

urlpatterns = [
    # Home and API
    path('', views.home, name='home'),
    path('student/<int:pk>/', views.student_detail, name='student_detail'),
    path('api/grades/', views.api_grades, name='api_grades'),

    # Student authentication and portal
    path('student/login/', views.student_login, name='student_login'),
    path('student/logout/', views.student_logout, name='student_logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('student/grades/', views.student_grades, name='student_grades'),
    path('student/profile/', views.student_profile, name='student_profile'),
    
    # PDF downloads (student)
    path('grades/download/', views.download_report_pdf, name='download_report_pdf'),
    
    # Admin/Teacher reports section
    path('reports/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('reports/bulk-download/', views.bulk_download_reports, name='bulk_download_reports'),
    path('reports/class-ranking/', views.class_ranking_report, name='class_ranking'),
    path('reports/class-ranking-pdf/', views.download_class_ranking_pdf, name='download_class_ranking_pdf'),
]