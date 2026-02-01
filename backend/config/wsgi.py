"""
WSGI config for Episteme project.

⚠️  WARNING: WSGI does not support streaming responses properly.
    Use ASGI (config.asgi) instead for production and development.
    
    Start with: uvicorn config.asgi:application --reload
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

application = get_wsgi_application()
