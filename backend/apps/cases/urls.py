"""
Case URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

case_router = DefaultRouter()
case_router.register(r'', views.CaseViewSet, basename='case')

urlpatterns = [
    path('', include(case_router.urls)),
]
