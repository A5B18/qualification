"""URLs pour agents."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AgentSkillViewSet, AgentCertificationViewSet, PerformanceIndicatorViewSet

router = DefaultRouter()
router.register(r'skills',          AgentSkillViewSet,          basename='skill')
router.register(r'certifications',  AgentCertificationViewSet,  basename='certification')
router.register(r'performances',    PerformanceIndicatorViewSet, basename='performance')
urlpatterns = [path('', include(router.urls))]
