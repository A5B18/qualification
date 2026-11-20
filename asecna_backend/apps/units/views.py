"""Vues pour l'app units."""

from django.db.models import Count, Prefetch
from rest_framework import viewsets

from apps.accounts.models import AgentProfile
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
    serializer_class = UnitSerializer
    queryset = Unit.objects.none()

    def get_queryset(self):
        """
        Unités actives, avec leur effectif et leur chef déjà chargés.

        Le serializer interrogeait la base deux fois par unité (compte des
        agents, recherche du chef) : la page des unités partait en une
        cinquantaine de requêtes. L'effectif devient une annotation, et le
        chef un prefetch unique pour toute la page.
        """
        chefs = AgentProfile.objects.filter(
            user__user_roles__role='UNIT_CHIEF',
            user__user_roles__is_active=True,
            user__is_active=True,
        ).select_related('user')

        return (
            Unit.objects.filter(is_active=True)
            .annotate(agents_count_agg=Count('agents', distinct=True))
            .prefetch_related(Prefetch('agents', queryset=chefs, to_attr='chief_profiles'))
            .order_by('code')
        )

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            # `DEFAULT_PERMISSION_CLASSES` impose déjà l'authentification.
            return super().get_permissions()
        return [IsAdministrator()]
