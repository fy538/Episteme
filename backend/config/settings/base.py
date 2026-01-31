"""
Django settings for Episteme project.
Base settings shared across all environments.
"""
import os
from pathlib import Path
import environ

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Environment variables
env = environ.Env(
    DEBUG=(bool, False)
)

# Read .env file if it exists
environ.Env.read_env(os.path.join(BASE_DIR.parent, '.env'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY', default='django-insecure-dev-key-change-in-production')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party
    'rest_framework',
    'corsheaders',
    
    # Local apps
    'apps.common',
    'apps.auth_app',
    'apps.events',
    'apps.chat',
    'apps.cases',
    'apps.signals',
    'apps.inquiries',  # Phase 2
    'apps.agents',  # Phase 2B
    'apps.projects',  # Phase 2
    'apps.artifacts',  # Phase 2.4
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASES = {
    'default': env.db('DATABASE_URL', default='postgresql://episteme:episteme@localhost:5432/episteme')
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Media files
MEDIA_URL = 'media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DATETIME_FORMAT': '%Y-%m-%dT%H:%M:%S.%fZ',
}

# CORS settings
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[
    'http://localhost:3000',
    'http://127.0.0.1:3000',
])
CORS_ALLOW_CREDENTIALS = True

# Celery Configuration
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes

# Custom User Model (if needed later)
# AUTH_USER_MODEL = 'auth_app.User'

# LLM API Keys (Phase 1 - Signal Extraction)
OPENAI_API_KEY = env('OPENAI_API_KEY', default='')
ANTHROPIC_API_KEY = env('ANTHROPIC_API_KEY', default='')
GOOGLE_API_KEY = env('GOOGLE_API_KEY', default='')
DEEPSEEK_API_KEY = env('DEEPSEEK_API_KEY', default='')
GROQ_API_KEY = env('GROQ_API_KEY', default='')

# AI Model Strategy (Solo Founder Mode)
# Default models for different task types
AI_MODELS = {
    'reasoning': env('AI_MODEL_REASONING', default='openai:gpt-5-mini'),
    'fast': env('AI_MODEL_FAST', default='openai:gpt-5-mini'),
    'extraction': env('AI_MODEL_EXTRACTION', default='openai:gpt-5-mini'),
}

# Embedding Backend (Phase 2)
EMBEDDING_BACKEND = env('EMBEDDING_BACKEND', default='postgresql')
# Options: 'postgresql' (default), 'pgvector' (future), 'pinecone' (legacy)

# Pinecone (legacy - for backward compatibility during migration)
PINECONE_API_KEY = env('PINECONE_API_KEY', default='')
PINECONE_ENVIRONMENT = env('PINECONE_ENVIRONMENT', default='us-east-1')

# Vector Database (Phase 2 - Document Search)
PINECONE_API_KEY = env('PINECONE_API_KEY', default='')
PINECONE_ENVIRONMENT = env('PINECONE_ENVIRONMENT', default='us-east-1')

# Document Processing (Phase 2)
MAX_UPLOAD_SIZE = env.int('MAX_UPLOAD_SIZE', default=10485760)  # 10MB
ALLOWED_FILE_TYPES = env.list('ALLOWED_FILE_TYPES', default=['pdf', 'docx', 'txt', 'md'])
