from django.urls import path
from . import views

urlpatterns = [
    # Route Pasangan Baseline vs Optimized sesuai Modul
    path('lab/course-list/baseline/', views.course_list_baseline),
    path('lab/course-list/optimized/', views.course_list_optimized),
    path('lab/course-members/baseline/', views.course_members_baseline),
    path('lab/course-members/optimized/', views.course_members_optimized),
    path('lab/course-dashboard/baseline/', views.course_dashboard_baseline),
    path('lab/course-dashboard/optimized/', views.course_dashboard_optimized),
]