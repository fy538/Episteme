"""
Chat URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'threads', views.ChatThreadViewSet, basename='thread')
router.register(r'messages', views.MessageViewSet, basename='message')

urlpatterns = [
    path('', include(router.urls)),
    # Async endpoints (DRF doesn't support async actions, so define separately)
    path('threads/<uuid:thread_id>/companion-stream/', views.companion_stream, name='companion-stream'),
]
