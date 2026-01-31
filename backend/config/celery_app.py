import logging
import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

app = Celery('episteme')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

logger = logging.getLogger(__name__)

# Ensure Celery logging signals are registered
import apps.common.celery_logging  # noqa: F401


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    logger.info("celery_debug_task", extra={"request": repr(self.request)})
