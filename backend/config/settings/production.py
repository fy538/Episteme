"""
Production settings
"""
from .base import *

DEBUG = False

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')

# Security settings
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# TODO: Add Sentry or other monitoring
# import sentry_sdk
# from sentry_sdk.integrations.django import DjangoIntegration
# 
# sentry_sdk.init(
#     dsn=env('SENTRY_DSN'),
#     integrations=[DjangoIntegration()],
# )
