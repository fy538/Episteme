"""
Production settings for Fly.io deployment
"""
from .base import *

DEBUG = env.bool('DEBUG', default=False)

# Fly.io sets this, or you can override
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['episteme.fly.dev', '.fly.dev', 'localhost', '127.0.0.1'])

# Security settings
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# Static files (WhiteNoise)
MIDDLEWARE.insert(
    MIDDLEWARE.index('django.middleware.security.SecurityMiddleware') + 1,
    'whitenoise.middleware.WhiteNoiseMiddleware',
)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Database - Fly.io sets DATABASE_URL automatically
# Already configured in base.py via env.db()

# CORS for Vercel frontend
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS')
if not CORS_ALLOWED_ORIGINS:
    raise ValueError("CORS_ALLOWED_ORIGINS must be set in production (e.g. 'https://your-app.vercel.app').")

# Logging
LOGGING = LOGGING.copy()
LOGGING['handlers']['console']['formatter'] = 'json'

SENTRY_DSN = env('SENTRY_DSN', default='')
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        environment=env('SENTRY_ENVIRONMENT', default='production'),
        traces_sample_rate=env.float('SENTRY_TRACES_SAMPLE_RATE', default=0.1),
        send_default_pii=False,
    )
