"""
Celery application for Bluewave Academy.
This module is imported by siteproject/__init__.py so that
the Celery app is ready before Django's app registry is populated.
"""
import os
from celery import Celery

# Tell Celery which settings module to use
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "siteproject.settings")

app = Celery("bluewaveacademy")

# Namespace all Celery configuration keys with CELERY_ so they can
# sit in Django's settings without colliding with other variables.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover @shared_task decorated tasks in all installed apps.
app.autodiscover_tasks()
