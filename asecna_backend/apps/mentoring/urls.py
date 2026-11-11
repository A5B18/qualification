"""URLs pour mentoring."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MentoringRecordViewSet

router = DefaultRouter()
router.register(r'', MentoringRecordViewSet, basename='mentoring')
urlpatterns = [path('', include(router.urls))]
