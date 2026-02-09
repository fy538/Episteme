"""
URL Configuration for Episteme
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings

from apps.common.search_views import unified_search_view

urlpatterns = [
    path('admin/', admin.site.urls),

    # Unified search endpoint
    path('api/search/', unified_search_view, name='unified-search'),

    # API endpoints
    path('api/auth/', include('apps.auth_app.urls')),
    path('api/events/', include('apps.events.urls')),
    path('api/chat/', include('apps.chat.urls')),
    path('api/cases/', include('apps.cases.urls')),
    path('api/', include('apps.inquiries.urls')),  # Phase 2: inquiries
    path('api/', include('apps.projects.urls')),  # Phase 2: projects + documents + evidence
    path('api/working-documents/', include('apps.cases.document_urls')),  # Working documents
    path('api/', include('apps.skills.urls')),  # Skills system
    path('api/v2/', include('apps.graph.urls')),  # V2: Knowledge graph
]

# Debug toolbar (only in development)
if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass  # debug_toolbar not installed
