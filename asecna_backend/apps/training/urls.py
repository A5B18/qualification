"""URLs pour training."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SpecialtyViewSet, TrainingViewSet, CourseViewSet,
    InternshipViewSet, QualificationMaintenanceViewSet,
)

router = DefaultRouter()
router.register(r'specialties',     SpecialtyViewSet,               basename='specialty')
router.register(r'trainings',       TrainingViewSet,                basename='training')
router.register(r'courses',         CourseViewSet,                  basename='course')
router.register(r'internships',     InternshipViewSet,              basename='internship')
router.register(r'maintenances',    QualificationMaintenanceViewSet, basename='maintenance')
urlpatterns = [path('', include(router.urls))]
