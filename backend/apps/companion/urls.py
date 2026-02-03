"""
Companion URL configuration
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Router for viewsets
router = DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),
]
