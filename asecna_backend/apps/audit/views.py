"""Views pour audit (lecture seule — admin uniquement)."""

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from core.permissions import IsAdministrator
from .models import AuditLog, LoginHistory
from .serializers import AuditLogSerializer, LoginHistorySerializer


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Lecture seule des logs d'audit — admin uniquement."""
    # `select_related` : le serializer rend l'utilisateur de chaque ligne.
    queryset = AuditLog.objects.select_related('user').order_by('-timestamp')
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsAdministrator]

    def get_queryset(self):
        qs = super().get_queryset()
        # Filtres optionnels
        user_id = self.request.query_params.get('user')
        if user_id:
            qs = qs.filter(user_id=user_id)
        action = self.request.query_params.get('action')
        if action:
            qs = qs.filter(action=action)
        return qs


class LoginHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Lecture seule de l'historique de connexions — admin uniquement."""
    queryset = LoginHistory.objects.select_related('user').order_by('-timestamp')
    serializer_class = LoginHistorySerializer
    permission_classes = [IsAuthenticated, IsAdministrator]
