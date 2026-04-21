from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Route untuk dashboard Django Silk (Profiling)
    path('silk/', include('silk.urls', namespace='silk')), 
    # Route untuk menghubungkan ke file courses/urls.py
    path('', include('courses.urls')),                    
]