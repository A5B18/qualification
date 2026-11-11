"""URLs pour arcep."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ARCEPBookViewSet, ARCEPEntryViewSet, ARCEPSignatureViewSet

router = DefaultRouter()
router.register(r'books',      ARCEPBookViewSet,      basename='arcep-book')
router.register(r'entries',    ARCEPEntryViewSet,     basename='arcep-entry')
router.register(r'signatures', ARCEPSignatureViewSet, basename='arcep-signature')
urlpatterns = [path('', include(router.urls))]
