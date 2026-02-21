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
    # csrf_exempt required because these are raw async views, not DRF views
    path('threads/<uuid:thread_id>/unified-stream/', views.unified_stream, name='unified-stream'),
    path('threads/<uuid:thread_id>/structure/', views.thread_structure, name='thread-structure'),
    path('threads/<uuid:thread_id>/confirm-tool/', views.confirm_tool_action, name='confirm-tool-action'),
    path('threads/<uuid:thread_id>/research/', views.thread_research, name='thread-research'),
    path('threads/<uuid:thread_id>/episodes/', views.thread_episodes, name='thread-episodes'),
]
