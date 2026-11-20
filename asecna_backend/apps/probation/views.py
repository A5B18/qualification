"""Vues pour l'app probation — avec actions de finalisation et de score."""

import datetime
import logging

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from core.permissions import (
    IsApproverOrUnitChief, IsEvaluator, IsEvaluatorOrUnitChiefOrApprover,
)
from .models import ProbationPeriod
from .serializers import ProbationPeriodSerializer

logger = logging.getLogger(__name__)

#: Seuil metier ASECNA : l'evaluation de fin de periode est annoncee a J-14.
ALERT_DAYS = 14


class ProbationPeriodViewSet(viewsets.ModelViewSet):
    """
    CRUD des périodes d'essai.

    Permissions :
      - Lecture : agent concerné, chef d'unité, admin
      - Création : chef d'unité ou admin
      - Finaliser avec score : EVALUATEUR (soumet le score, passe à PASSED/FAILED)
      - Valider le score : CHEF_UNITE/APPROBATEUR

    Actions supplémentaires :
      POST .../finalize/  → Évaluateur saisit le score → PASSED ou FAILED
      POST .../due/       → Liste des sessions dont l'évaluation est due (J-14)
    """
    serializer_class = ProbationPeriodSerializer
    # Jamais consulte a l'execution (get_queryset ci-dessous le remplace) ;
    # present pour que drf-spectacular type le parametre de chemin `id`
    # en entier au lieu de le deduire d'un get_queryset() qui echoue
    # hors requete.
    queryset = ProbationPeriod.objects.none()

    def get_queryset(self):
        user = self.request.user
        base = ProbationPeriod.objects.select_related('agent', 'evaluated_by')
        if user.is_admin or user.has_any_role('UNIT_CHIEF', 'APPROVER', 'EVALUATOR'):
            qs = base.all()
        else:
            # Agent : uniquement ses propres périodes
            qs = base.filter(agent=user)
        # Filtres ?agent= / ?probation_status= utilisés par le frontend
        agent_id = self.request.query_params.get('agent')
        if agent_id:
            qs = qs.filter(agent_id=agent_id)
        probation_status = self.request.query_params.get('probation_status')
        if probation_status:
            qs = qs.filter(probation_status=probation_status)
        return qs.order_by('-start_date', '-id')

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        if self.action == 'finalize':
            # L'évaluateur saisit le score et finalise
            return [IsAuthenticated(), IsEvaluator()]
        if self.action == 'evaluation_due':
            # Alerte J-14 : ouverte aux évaluateurs, chefs d'unité et approbateurs.
            # Avant, cette action retombait sur IsApproverOrUnitChief et renvoyait
            # donc 403 aux EVALUATEURS, alors que le corps de la vue les autorise.
            return [IsAuthenticated(), IsEvaluatorOrUnitChiefOrApprover()]
        # Création, mise à jour, suppression → chef d'unité ou admin
        return [IsAuthenticated(), IsApproverOrUnitChief()]

    @action(detail=True, methods=['post'], url_path='finalize')
    def finalize(self, request, pk=None):
        """
        EVALUATEUR : saisit le score final et clôture la période d'essai.
        Règles métier :
          - Score >= 70 → PASSED (et met à jour le statut AgentProfile vers MENTORED)
          - Score < 70  → FAILED (et déclenchement éventuel 2ème tentative ou RETIRED)
        Body : { score, unit_chief_comment, mentor_comment }
        """
        period = self.get_object()

        if period.probation_status != ProbationPeriod.ProbationStatus.IN_PROGRESS:
            return Response(
                {'error': {'code': 'bad_request',
                           'message': 'Seules les périodes en cours peuvent être finalisées.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        score = request.data.get('score')
        if score is None:
            return Response(
                {'error': {'code': 'bad_request', 'message': 'Le score est obligatoire.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            score = float(score)
        except (TypeError, ValueError):
            return Response(
                {'error': {'code': 'bad_request', 'message': 'Le score doit être un nombre.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not (0 <= score <= 100):
            return Response(
                {'error': {'code': 'bad_request', 'message': 'Le score doit être compris entre 0 et 100.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Appliquer les règles métier
        period.score = score
        period.evaluated_by = request.user
        period.actual_end_date = timezone.now().date()
        period.unit_chief_comment = request.data.get('unit_chief_comment', period.unit_chief_comment)
        period.mentor_comment = request.data.get('mentor_comment', period.mentor_comment)

        if score >= ProbationPeriod.PASSING_SCORE:
            # Réussite : 70/100 minimum
            period.probation_status = ProbationPeriod.ProbationStatus.PASSED
            # Mettre à jour le statut de l'agent → en attente de mentorat
            _update_agent_status_after_probation(period.agent, passed=True)
        else:
            period.probation_status = ProbationPeriod.ProbationStatus.FAILED
            if period.is_last_attempt:
                # 2ème tentative échouée → agent non retenu
                _update_agent_status_after_probation(period.agent, passed=False, final=True)

        period.save()
        return Response(ProbationPeriodSerializer(period).data)

    @action(detail=False, methods=['get'], url_path='evaluation-due')
    def evaluation_due(self, request):
        """
        Périodes d'essai dont l'évaluation est due (à J-14 ou moins).

        L'habilitation est portée par `get_permissions`
        (`IsEvaluatorOrUnitChiefOrApprover`). Le contrôle de rôle écrit ici en
        plus excluait les APPROBATEURS que la classe de permission autorise :
        ils franchissaient la permission pour recevoir un 403 du corps de la
        vue. Deux règles pour une même porte, et elles ne disaient pas la même
        chose.
        """
        threshold = timezone.localdate() + datetime.timedelta(days=ALERT_DAYS)
        due = ProbationPeriod.objects.filter(
            probation_status=ProbationPeriod.ProbationStatus.IN_PROGRESS,
            end_date__lte=threshold,
        ).select_related('agent', 'evaluated_by').order_by('end_date')

        serializer = self.get_serializer(due, many=True)
        # `len()` sur la liste deja serialisee : `due.count()` relancait une
        # requete COUNT sur un queryset deja parcouru.
        return Response({'count': len(serializer.data), 'results': serializer.data})


def _update_agent_status_after_probation(agent, passed: bool, final: bool = False):
    """
    Met à jour le statut du parcours agent après la fin de sa période d'essai.
    passed=True → statut MENTORED (début du mentorat)
    passed=False, final=True → statut RETIRED (non retenu)

    Un agent sans profil de parcours n'a rien à mettre à jour : c'est le seul
    cas toléré, et il est nommé. L'ancien `except Exception: pass` masquait
    aussi les erreurs de base de données — une période pouvait passer à PASSED
    sans que l'agent entre en mentorat, silencieusement.
    """
    from apps.accounts.models import AgentProfile, AgentStatus

    if not passed and not final:
        # Échec non définitif : l'agent garde son statut, une seconde
        # tentative reste ouverte.
        return

    try:
        profile = agent.agent_profile
    except AgentProfile.DoesNotExist:
        logger.info(
            "Fin de période d'essai de l'agent %s : aucun profil de parcours "
            "à mettre à jour.", agent.pk,
        )
        return

    profile.status = AgentStatus.MENTORED if passed else AgentStatus.RETIRED
    profile.save(update_fields=['status'])
