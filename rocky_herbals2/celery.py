# rocky_herbals2/celery.py
from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab

# set default Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rocky_herbals2.settings')

app = Celery('rocky_herbals2')

# Load settings from Django settings, CELERY_ namespace
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

# -------------------------------
# Optional: Debug helper task
# -------------------------------
@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

# -------------------------------
# Daily MLM Engine Beat Schedule
# -------------------------------
app.conf.beat_schedule = {
    'run-mlm-daily-engine': {
        'task': 'herbalapp.tasks.run_engine_task',
        'schedule': crontab(hour=0, minute=0),  # every day at midnight
        'options': {'queue': 'mlm_engine'},
    },
}

