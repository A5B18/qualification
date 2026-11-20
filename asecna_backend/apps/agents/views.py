"""Views pour agents — compétences, certifications, indicateurs de performance."""

from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied

from core.permissions import IsEvaluator
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


class OwnRecordWriteMixin:
    """
    Un agent n'ecrit que dans son propre dossier ; l'administrateur partout.

    Les trois ViewSets de l'app repetaient ce controle, et pas au meme
    endroit : les competences le posaient sur la creation, la modification et
    la suppression, les certifications seulement sur les deux premieres. Un
    chef d'unite — qui voit toutes les certifications — pouvait donc en
    supprimer une qui ne le concernait pas, alors que la modifier lui etait
    refuse. Le controle est desormais ecrit une fois et s'applique aux trois
    verbes.
    """

    #: Verbe employe dans le message de refus (« ajouter », « declarer »...).
    own_record_label = 'modifier'

    def _assert_owns(self, agent) -> None:
        user = self.request.user
        if not user.is_admin and agent != user:
            raise PermissionDenied(
                f"Vous ne pouvez {self.own_record_label} que vos propres éléments."
            )

    def perform_create(self, serializer):
        agent = serializer.validated_data.get('agent', self.request.user)
        self._assert_owns(agent)
        serializer.save(agent=agent)

    def perform_update(self, serializer):
        # `serializer.instance` est l'objet deja charge par la vue :
        # `self.get_object()` relancait la meme requete.
        self._assert_owns(serializer.instance.agent)
        serializer.save()

    def perform_destroy(self, instance):
        self._assert_owns(instance.agent)
        instance.delete()


class AgentSkillViewSet(OwnRecordWriteMixin, viewsets.ModelViewSet):
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
        if user.is_admin or user.has_any_role('UNIT_CHIEF', 'EVALUATOR'):
            qs = AgentSkill.objects.all().select_related('agent').order_by('agent', 'name')
        else:
            qs = AgentSkill.objects.filter(agent=user).order_by('name')
        return filter_by_agent(qs, self.request)

    own_record_label = 'gérer'


class AgentCertificationViewSet(OwnRecordWriteMixin, viewsets.ModelViewSet):
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
        if user.is_admin or user.has_any_role('UNIT_CHIEF', 'APPROVER'):
            qs = AgentCertification.objects.all().select_related('agent').order_by('-issue_date')
        else:
            qs = AgentCertification.objects.filter(agent=user).order_by('-issue_date')
        return filter_by_agent(qs, self.request)

    own_record_label = 'déclarer'


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
        if user.is_admin or user.has_any_role('EVALUATOR', 'UNIT_CHIEF'):
            qs = PerformanceIndicator.objects.all().select_related('agent', 'evaluator').order_by('-year')
        else:
            qs = PerformanceIndicator.objects.filter(agent=user).order_by('-year')
        return filter_by_agent(qs, self.request)

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            # `DEFAULT_PERMISSION_CLASSES` impose deja l'authentification.
            return super().get_permissions()
        # Seul un évaluateur ou admin peut créer/modifier un indicateur
        return [IsEvaluator()]

    def perform_create(self, serializer):
        serializer.save(evaluator=self.request.user)
