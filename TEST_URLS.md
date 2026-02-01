# URL Debugging

Based on your URL configuration:

## Cases App URLs (`api/cases/` prefix)
- `/api/cases/` - Case list/create
- `/api/cases/{id}/` - Case detail
- `/api/cases/documents/` - **CaseDocument list** ✅
- `/api/cases/documents/{id}/` - CaseDocument detail
- `/api/cases/working-views/` - WorkingView list

## Projects App URLs (`api/` prefix)
- `/api/projects/` - Project list
- `/api/documents/` - **Document list** (different model!)
- `/api/evidence/` - Evidence list

## The Issue

Frontend calls: `/api/cases/documents/?case={id}`  
Backend should serve: `CaseDocumentViewSet` at this URL

**404 suggests**: Either the ViewSet isn't registered or there's a permission issue.

## Quick Test

In your browser or curl:
```bash
# Test if endpoint exists (should return 401 or 200, not 404)
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/cases/documents/

# If 404 = URL not registered
# If 401 = URL exists but needs auth
# If 200 = URL works!
```

## Possible Fixes

1. **Check router registration** - CaseDocumentViewSet might not be imported
2. **Check URL include order** - projects.urls might override
3. **Use full path** - Change router registration to avoid conflicts
