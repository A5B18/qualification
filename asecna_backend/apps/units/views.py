"""Vues pour l'app units."""

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from core.permissions import IsAdministrator
from core.mixins import SoftDeleteMixin
from .models import Unit
from .serializers import UnitSerializer


class UnitViewSet(SoftDeleteMixin, viewsets.ModelViewSet):
    """
    CRUD des unités.
    - Lecture : tout utilisateur authentifié.
    - Écriture : administrateur uniquement.
    """
    queryset = Unit.objects.filter(is_active=True).order_by('code')
    serializer_class = UnitSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdministrator()]
