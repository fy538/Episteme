"""
URL configuration for reasoning app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.reasoning.views import KnowledgeGraphViewSet

router = DefaultRouter()
router.register(r'knowledge-graph', KnowledgeGraphViewSet, basename='knowledge-graph')

urlpatterns = [
    path('', include(router.urls)),
]
