# Debugging 404: /api/cases/documents/

## What's Happening

Frontend calls: `GET /api/cases/documents/?case={id}`  
Backend returns: `404 Not Found`

## Why This Happens

The `/api/cases/documents/` endpoint exists in code but returns 404. Possible causes:

### 1. URL Router Issue (Most Likely)

The `cases/urls.py` registers:
```python
router.register(r'', views.CaseViewSet, basename='case')
router.register(r'documents', views.CaseDocumentViewSet, basename='case-document')
```

When both are at the base of the same router, there can be conflicts.

**Fix**: Register cases at a named path instead of empty string.

**In `backend/apps/cases/urls.py`**:
```python
router = DefaultRouter()
router.register(r'cases', views.CaseViewSet, basename='case')  # Changed from r''
router.register(r'working-views', views.WorkingViewViewSet, basename='working-view')
router.register(r'documents', views.CaseDocumentViewSet, basename='case-document')
```

**But this changes the URL!** From `/api/cases/` to `/api/cases/cases/`

### 2. Alternative Fix: Separate the Routers

Keep the current setup but check if `CaseDocumentViewSet` is actually being registered.

## Quick Test

Run this in Docker:
```bash
docker-compose exec backend python manage.py shell
```

Then:
```python
from apps.cases.views import CaseDocumentViewSet
from apps.cases.models import CaseDocument

# Check viewset exists
print(CaseDocumentViewSet)

# Check if any documents exist
print(CaseDocument.objects.count())

exit()
```

## Temporary Workaround

The `/api/cases/documents/` endpoint might not be critical for basic case functionality. You can:

1. Continue testing other features (chat, cases, settings)
2. Debug this endpoint separately
3. Or use the project documents endpoint instead

## What IS Working

From your logs:
- ✅ Chat (Claude API working)
- ✅ Case creation
- ✅ Preferences API
- ✅ Inquiries

The documents endpoint is one piece that needs debugging, but the core app is functional!
