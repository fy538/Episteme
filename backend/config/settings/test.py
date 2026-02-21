"""
Test settings — connects to PostgreSQL on localhost:5433 (Docker Compose host port).

Usage:
    DJANGO_SETTINGS_MODULE=config.settings.test pytest apps/graph/tests_thematic_summary.py -v

Or permanently in pytest.ini by overriding the default DJANGO_SETTINGS_MODULE.
"""
from .development import *  # noqa: F401,F403

# Override database to use the Docker Compose PostgreSQL via host port mapping.
# Docker maps container port 5432 → host port 5433.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'episteme',
        'USER': 'episteme',
        'PASSWORD': 'episteme',
        'HOST': 'localhost',
        'PORT': '5433',
        'TEST': {
            'NAME': 'test_episteme',
        },
    }
}

# Disable debug toolbar in tests (avoids middleware issues)
INSTALLED_APPS = [
    app for app in INSTALLED_APPS
    if app != 'debug_toolbar'
]
MIDDLEWARE = [
    mw for mw in MIDDLEWARE
    if mw != 'debug_toolbar.middleware.DebugToolbarMiddleware'
]

# Use synchronous responses in tests (no Celery)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
