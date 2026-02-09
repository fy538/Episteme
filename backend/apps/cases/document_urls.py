"""
WorkingDocument URL configuration.

Mounted at /api/working-documents/ in config/urls.py.
"""
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'', views.WorkingDocumentViewSet, basename='working-document')

urlpatterns = router.urls
