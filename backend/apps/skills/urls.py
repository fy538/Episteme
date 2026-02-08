from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SkillViewSet, SkillPackViewSet

router = DefaultRouter()
router.register(r'skills', SkillViewSet, basename='skill')
router.register(r'skill-packs', SkillPackViewSet, basename='skill-pack')

urlpatterns = [
    path('', include(router.urls)),
]
