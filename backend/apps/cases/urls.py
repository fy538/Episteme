"""
Case URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

# Separate routers to avoid conflicts
case_router = DefaultRouter()
case_router.register(r'', views.CaseViewSet, basename='case')
case_router.register(r'working-views', views.WorkingViewViewSet, basename='working-view')

document_router = DefaultRouter()
document_router.register(r'', views.CaseDocumentViewSet, basename='case-document')

urlpatterns = [
    path('documents/', include(document_router.urls)),
    path('', include(case_router.urls)),
]
