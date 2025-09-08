# labour_crm/celery.py

import os
from celery import Celery
# import eventlet
# eventlet.monkey_patch()

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'labour_crm.settings')

app = Celery('labour_crm')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()