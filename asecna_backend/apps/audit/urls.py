"""URLs pour audit."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AuditLogViewSet, LoginHistoryViewSet

router = DefaultRouter()
router.register(r'logs',     AuditLogViewSet,     basename='audit-log')
router.register(r'logins',   LoginHistoryViewSet, basename='login-history')
urlpatterns = [path('', include(router.urls))]
