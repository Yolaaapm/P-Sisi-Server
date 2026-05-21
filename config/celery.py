import os
from celery import Celery

# Set default Django settings module untuk celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('simple_lms')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()