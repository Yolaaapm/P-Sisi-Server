from django.contrib import admin
from django.urls import path, include
from courses.api import api 

urlpatterns = [
    path('admin/', admin.site.urls),
    path('silk/', include('silk.urls', namespace='silk')), 
    path('', include('courses.urls')), 
    path('api/', api.urls),    
]