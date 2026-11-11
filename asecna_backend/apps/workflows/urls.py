"""URLs pour workflows."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ApprovalWorkflowViewSet

router = DefaultRouter()
router.register(r'', ApprovalWorkflowViewSet, basename='workflow')
urlpatterns = [path('', include(router.urls))]
