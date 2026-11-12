"""Views pour agents — compétences, certifications, indicateurs de performance."""

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from core.permissions import IsAdministrator, IsEvaluator, IsApproverOrUnitChief
from .models import AgentSkill, AgentCertification, PerformanceIndicator
from .serializers import AgentSkillSerializer, AgentCertificationSerializer, PerformanceIndicatorSerializer


def filter_by_agent(queryset, request):
    """
    Applique le filtre `?agent=<id>` commun aux trois ressources.

    La fiche d'un agent affiche ses competences, ses certifications et ses
    performances : sans ce filtre, chaque onglet recevait la table entiere et
    devait trier dans le navigateur — donc des donnees d'autres agents
    transitaient inutilement, et la pagination tronquait le resultat avant
    meme le tri.
    """
    agent_id = request.query_params.get('agent')
    if agent_id:
        queryset = queryset.filter(agent_id=agent_id)
    return queryset


class AgentSkillViewSet(viewsets.ModelViewSet):
    """
    Compétences d'un agent.

    Permissions :
      - Lecture : agent (ses compétences) + UNIT_CHIEF + ADMIN
      - Création : agent (uniquement pour lui-même) ou ADMIN
      - Modification/suppression : agent concerné ou ADMIN
    """
    serializer_class = AgentSkillSerializer
    # Jamais consulte a l'execution (get_queryset ci-dessous le remplace) ;
    # present pour que drf-spectacular type le parametre de chemin `id`
    # en entier au lieu de le deduire d'un get_queryset() qui echoue
    # hors requete.
    queryset = AgentSkill.objects.none()

    def get_queryset(self):
        user = self.request.user
        if user.is_admin or user.has_role('UNIT_CHIEF') or user.has_role('EVALUATOR'):
            qs = AgentSkill.objects.all().select_related('agent').order_by('agent', 'name')
        else:
            qs = AgentSkill.objects.filter(agent=user).order_by('name')
        return filter_by_agent(qs, self.request)

    def get_permissions(self):
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        """L'agent ne peut créer que ses propres compétences (sauf admin)."""
        user = self.request.user
        agent = serializer.validated_data.get('agent', user)
        if not user.is_admin and agent != user:
            raise PermissionDenied("Vous ne pouvez ajouter que vos propres compétences.")
        serializer.save(agent=agent)

    def perform_update(self, serializer):
        """L'agent ne peut modifier que ses propres compétences."""
        user = self.request.user
        if not user.is_admin and self.get_object().agent != user:
            raise PermissionDenied("Vous ne pouvez modifier que vos propres compétences.")
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        if not user.is_admin and instance.agent != user:
            raise PermissionDenied("Vous ne pouvez supprimer que vos propres compétences.")
        instance.delete()


class AgentCertificationViewSet(viewsets.ModelViewSet):
    """
    Certifications d'un agent.

    Permissions :
      - Lecture : agent (ses certifications) + UNIT_CHIEF + ADMIN
      - Création : agent (uniquement pour lui-même) ou ADMIN
    """
    serializer_class = AgentCertificationSerializer
    # Jamais consulte a l'execution (get_queryset ci-dessous le remplace) ;
    # present pour que drf-spectacular type le parametre de chemin `id`
    # en entier au lieu de le deduire d'un get_queryset() qui echoue
    # hors requete.
    queryset = AgentCertification.objects.none()

    def get_queryset(self):
        user = self.request.user
        if user.is_admin or user.has_role('UNIT_CHIEF') or user.has_role('APPROVER'):
            qs = AgentCertification.objects.all().select_related('agent').order_by('-issue_date')
        else:
            qs = AgentCertification.objects.filter(agent=user).order_by('-issue_date')
        return filter_by_agent(qs, self.request)

    def get_permissions(self):
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        user = self.request.user
        agent = serializer.validated_data.get('agent', user)
        if not user.is_admin and agent != user:
            raise PermissionDenied("Vous ne pouvez déclarer que vos propres certifications.")
        serializer.save(agent=agent)

    def perform_update(self, serializer):
        user = self.request.user
        if not user.is_admin and self.get_object().agent != user:
            raise PermissionDenied("Vous ne pouvez modifier que vos propres certifications.")
        serializer.save()


class PerformanceIndicatorViewSet(viewsets.ModelViewSet):
    """
    Indicateurs de performance.

    Permissions :
      - Lecture : agent (ses propres) + UNIT_CHIEF + EVALUATOR + ADMIN
      - Création/modification : EVALUATEUR ou ADMIN uniquement
        (règle métier : seul un évaluateur peut noter un agent)
    """
    serializer_class = PerformanceIndicatorSerializer
    # Jamais consulte a l'execution (get_queryset ci-dessous le remplace) ;
    # present pour que drf-spectacular type le parametre de chemin `id`
    # en entier au lieu de le deduire d'un get_queryset() qui echoue
    # hors requete.
    queryset = PerformanceIndicator.objects.none()

    def get_queryset(self):
        user = self.request.user
        if user.is_admin or user.has_role('EVALUATOR') or user.has_role('UNIT_CHIEF'):
            qs = PerformanceIndicator.objects.all().select_related('agent', 'evaluator').order_by('-year')
        else:
            qs = PerformanceIndicator.objects.filter(agent=user).order_by('-year')
        return filter_by_agent(qs, self.request)

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        # Seul un évaluateur ou admin peut créer/modifier un indicateur
        return [IsAuthenticated(), IsEvaluator()]

    def perform_create(self, serializer):
        serializer.save(evaluator=self.request.user)
