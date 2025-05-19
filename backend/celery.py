import os
from celery import Celery
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
app = Celery('backend')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.timezone = 'Asia/Kolkata'

app.conf.beat_schedule = {
    "every_thirty_seconds": {
        "task": "api_agent_backend.task.check_pending_evaluations",
        "schedule": timedelta(seconds=300),
    },
}

app.autodiscover_tasks()


import api_agent_backend.task
