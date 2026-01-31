"""
Case URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'', views.CaseViewSet, basename='case')
router.register(r'working-views', views.WorkingViewViewSet, basename='working-view')
router.register(r'documents', views.CaseDocumentViewSet, basename='case-document')

urlpatterns = [
    path('', include(router.urls)),
]
