"""
Signal URLs (Phase 1)
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'', views.SignalViewSet, basename='signal')

urlpatterns = [
    path('', include(router.urls)),
]
