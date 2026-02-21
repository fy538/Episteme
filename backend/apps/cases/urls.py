"""
Case URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views
from . import streaming_views

case_router = DefaultRouter()
case_router.register(r'', views.CaseViewSet, basename='case')

urlpatterns = [
    # SSE streaming endpoint for extraction progress (outside DRF router)
    path(
        '<uuid:case_id>/extraction/stream/',
        streaming_views.case_extraction_stream,
        name='case-extraction-stream',
    ),
    # Standard DRF routes
    path('', include(case_router.urls)),
]
