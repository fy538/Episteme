"""
Project URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views
from . import search_views
from . import evidence_views  # Phase 2.2

router = DefaultRouter()
router.register(r'projects', views.ProjectViewSet, basename='project')
router.register(r'documents', views.DocumentViewSet, basename='document')
router.register(r'evidence', evidence_views.EvidenceViewSet, basename='evidence')  # Phase 2.2

urlpatterns = [
    path('', include(router.urls)),
    path('documents/semantic-search/', search_views.search_documents, name='document-search'),
]
