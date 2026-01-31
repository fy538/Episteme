"""
Celery instance - re-exported from config.celery_app for convenience
This allows running: celery -A tasks.celery worker
"""
from config.celery_app import app

__all__ = ('app',)
