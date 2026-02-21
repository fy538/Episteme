"""
Project URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views
from . import search_views
from . import streaming_views
from . import concierge_views

router = DefaultRouter()
router.register(r'projects', views.ProjectViewSet, basename='project')
router.register(r'documents', views.DocumentViewSet, basename='document')

urlpatterns = [
    path('', include(router.urls)),
    path('documents/semantic-search/', search_views.search_documents, name='document-search'),
    path(
        'documents/<uuid:document_id>/processing-stream/',
        streaming_views.document_processing_stream,
        name='document-processing-stream',
    ),
    path(
        'projects/<uuid:pk>/concierge/',
        concierge_views.project_concierge,
        name='project-concierge',
    ),
]
