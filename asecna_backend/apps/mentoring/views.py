"""Vues pour l'app mentoring."""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction

from core.permissions import IsMentor, IsApproverOrUnitChief
from apps.workflows import services as workflows
from .models import MentoringRecord
from .serializers import (
    MentoringRecordSerializer,
    MentoringSubmitSerializer,
    MentoringDecisionSerializer,
)

User = get_user_model()


class MentoringRecordViewSet(viewsets.ModelViewSet):
    """
    CRUD des fiches de mentorat avec actions workflow.

    POST .../submit/  → Soumettre au chef d'unité (mentor)
    POST .../approve/ → Approuver (chef d'unité)
    POST .../reject/  → Rejeter (chef d'unité)
    """
    serializer_class = MentoringRecordSerializer
    # Jamais consulte a l'execution (get_queryset ci-dessous le remplace) ;
    # present pour que drf-spectacular type le parametre de chemin `id`
    # en entier au lieu de le deduire d'un get_queryset() qui echoue
    # hors requete.
    queryset = MentoringRecord.objects.none()

    def get_queryset(self):
        user = self.request.user
        base = MentoringRecord.objects.select_related('agent', 'mentor', 'unit_chief')
        if user.is_admin or user.has_any_role('UNIT_CHIEF', 'APPROVER'):
            qs = base.all()
        elif user.has_role('MENTOR'):
            qs = base.filter(mentor=user)
        else:
            qs = base.filter(agent=user)
        # Filtres ?agent= / ?mentor= / ?mentoring_status= utilisés par le frontend
        agent_id = self.request.query_params.get('agent')
        if agent_id:
            qs = qs.filter(agent_id=agent_id)
        mentor_id = self.request.query_params.get('mentor')
        if mentor_id:
            qs = qs.filter(mentor_id=mentor_id)
        mentoring_status = self.request.query_params.get('mentoring_status')
        if mentoring_status:
            qs = qs.filter(mentoring_status=mentoring_status)
        return qs.order_by('-created_at', '-id')

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        if self.action in ('approve', 'reject'):
            return [IsAuthenticated(), IsApproverOrUnitChief()]
        return [IsAuthenticated(), IsMentor()]

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Soumettre la fiche au chef d'unité."""
        record = self.get_object()
        serializer = MentoringSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            chief = User.objects.get(pk=serializer.validated_data['unit_chief'])
            with transaction.atomic():
                record.submit(unit_chief=chief)
                # Le decideur est connu des la soumission pour une fiche de
                # mentorat : on l'inscrit au registre.
                workflows.record_submission(
                    record, submitted_by=request.user, unit_chief=chief,
                )
            return Response(MentoringRecordSerializer(record).data)
        except User.DoesNotExist:
            return Response({'error': {'code': 'not_found', 'message': 'Chef d\'unité introuvable.'}},
                            status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response({'error': {'code': 'bad_request', 'message': str(e.message)}},
                            status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approuver la fiche (chef d'unité)."""
        record = self.get_object()
        serializer = MentoringDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        opinion = serializer.validated_data.get('opinion', '')
        try:
            with transaction.atomic():
                record.approve(opinion=opinion)
                workflows.record_approval(
                    record, approver=request.user, comment=opinion,
                    as_unit_chief=True,
                )
            return Response(MentoringRecordSerializer(record).data)
        except ValidationError as e:
            return Response({'error': {'code': 'bad_request', 'message': str(e.message)}},
                            status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Rejeter la fiche (chef d'unité)."""
        record = self.get_object()
        serializer = MentoringDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        opinion = serializer.validated_data.get('opinion', '')
        try:
            with transaction.atomic():
                record.reject(opinion=opinion)
                workflows.record_rejection(
                    record, approver=request.user, reason=opinion,
                    as_unit_chief=True,
                )
            return Response(MentoringRecordSerializer(record).data)
        except ValidationError as e:
            return Response({'error': {'code': 'bad_request', 'message': str(e.message)}},
                            status=status.HTTP_400_BAD_REQUEST)
