# Quick Start Guide - Get Episteme Running

## The Issue You're Seeing

The frontend shows "Loading..." because the backend requires authentication, but we haven't set up login yet.

## Quick Fix: Disable Auth for Development

### Option 1: Allow Anonymous Access (Fastest)

Update [`backend/config/settings/development.py`](../backend/config/settings/development.py):

```python
# Add this to override base.py for development
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',  # Allow unauthenticated in dev
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
}
```

Then restart Django:
```bash
cd backend
python manage.py runserver
```

Now the frontend will work without authentication!

### Option 2: Create Test User & Token

```bash
cd backend
python manage.py shell
```

```python
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken

# Create test user
user = User.objects.create_user(
    username='test',
    email='test@example.com',
    password='testpass123'
)

# Get JWT token
refresh = RefreshToken.for_user(user)
access_token = str(refresh.access_token)

print(f"\nAccess Token:\n{access_token}\n")
print("Add this to frontend localStorage:")
print(f"localStorage.setItem('auth_token', '{access_token}');")
```

Then in browser console (localhost:3000):
```javascript
localStorage.setItem('auth_token', 'YOUR_TOKEN_HERE');
```

Reload the page.

## Full Startup Sequence

### 1. Backend

```bash
cd backend

# Run migrations (first time only)
python manage.py makemigrations
python manage.py migrate

# Create superuser (first time only)  
python manage.py createsuperuser

# Start Django
python manage.py runserver
```

### 2. Celery (for signal extraction)

```bash
cd backend
celery -A config.celery_app worker -l info
```

### 3. Frontend

```bash
cd frontend
npm install  # First time only
npm run dev
```

## What You Should See

**When working:**

1. **Landing page (localhost:3000)**
   - "Episteme" heading
   - "Start Chatting" button

2. **Chat page (localhost:3000/chat)**
   - Chat interface on left
   - Structure sidebar on right
   - Can send messages
   - AI responses appear
   - Signals appear in sidebar

3. **After chatting:**
   - Signals: "Claim: ...", "Assumption: ...", etc.
   - "Create Case" button appears
   - After case created: Inquiry suggestions
   - Can navigate to case workspace

## Troubleshooting

### "Loading..." Forever

**Check:**
1. Is Django running? Visit http://localhost:8000/api/
2. Check browser console (F12) for errors
3. Check Django logs for errors
4. Try Option 1 above (disable auth)

### "Cannot connect to backend"

**Fix:**
- Ensure Django is on port 8000
- Check `.env.local` has correct URL
- Check CORS settings allow localhost:3000

### "401 Unauthorized"

**Fix:**
- Use Option 1 (disable auth for dev)
- Or Option 2 (create token)

### Signals Not Appearing

**Fix:**
- Ensure Celery is running
- Check Celery logs for errors
- Signals extract async (takes 2-5 seconds)

## Development Settings Recommendation

For smooth development, add this file:

**Create:** `backend/config/settings/development.py`

```python
from .base import *

DEBUG = True

# Allow anonymous access in development
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',  # No auth required
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
}

# CORS - allow frontend
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]
```

Then run Django with dev settings:
```bash
export DJANGO_SETTINGS_MODULE=config.settings.development
python manage.py runserver
```

Or set in `.env`:
```
DJANGO_SETTINGS_MODULE=config.settings.development
```

## Next Steps After It's Running

1. **Chat** - Send messages, see signals
2. **Create case** - When signals appear
3. **Navigate** - Go to `/cases/{case-id}`
4. **Edit brief** - Open case brief, start writing
5. **Citations** - Type `[[` to see autocomplete

## Need Help?

**Check:**
- Backend logs (terminal running Django)
- Frontend logs (browser console F12)
- Celery logs (terminal running Celery)

**Common commands:**
```bash
# Check if Django is responding
curl http://localhost:8000/api/

# Check if frontend can reach backend
curl http://localhost:8000/api/chat/threads/

# Create test user
python manage.py createsuperuser
```

---

**Most likely fix: Use Option 1 above to disable auth for development!**
