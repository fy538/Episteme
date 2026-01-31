"""
URL configuration for inquiries app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.inquiries.views import InquiryViewSet, EvidenceViewSet, ObjectionViewSet

router = DefaultRouter()
router.register(r'inquiries', InquiryViewSet, basename='inquiry')
router.register(r'evidence', EvidenceViewSet, basename='evidence')
router.register(r'objections', ObjectionViewSet, basename='objection')

urlpatterns = [
    path('', include(router.urls)),
]
