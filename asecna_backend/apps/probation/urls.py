"""URLs pour probation."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProbationPeriodViewSet

router = DefaultRouter()
router.register(r'', ProbationPeriodViewSet, basename='probation')
urlpatterns = [path('', include(router.urls))]
