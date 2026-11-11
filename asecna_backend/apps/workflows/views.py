"""
Views pour l'app workflows — Pipeline d'approbation générique.

Actions disponibles :
  POST .../submit/   → soumettre un workflow (DRAFT → SUBMITTED)
  POST .../approve/  → approuver (SUBMITTED → APPROVED)
  POST .../reject/   → rejeter avec motif (SUBMITTED → REJECTED)
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from core.permissions import IsApproverOrUnitChief
from .models import ApprovalWorkflow
from .serializers import ApprovalWorkflowSerializer


class ApprovalWorkflowViewSet(viewsets.ModelViewSet):
    """
    CRUD + actions du pipeline d'approbation.

    Filtres disponibles (query params) :
      ?workflow_status=DRAFT|SUBMITTED|APPROVED|REJECTED
      ?content_type=<id>
      ?object_id=<id>
    """
    serializer_class = ApprovalWorkflowSerializer

    def get_queryset(self):
        qs = ApprovalWorkflow.objects.all().select_related(
            'submitted_by', 'approver', 'unit_chief', 'content_type'
        ).order_by('-created_at')

        # Filtres optionnels
        wf_status = self.request.query_params.get('workflow_status')
        if wf_status:
            qs = qs.filter(workflow_status=wf_status)

        ct_id = self.request.query_params.get('content_type')
        if ct_id:
            qs = qs.filter(content_type_id=ct_id)

        obj_id = self.request.query_params.get('object_id')
        if obj_id:
            qs = qs.filter(object_id=obj_id)

        return qs

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'submit'):
            return [IsAuthenticated()]
        # approve / reject / create / update / delete → chef d'unité ou approbateur
        return [IsAuthenticated(), IsApproverOrUnitChief()]

    def perform_create(self, serializer):
        serializer.save(submitted_by=self.request.user)

    # ── Actions métier ────────────────────────────────────────────────────────

    @action(detail=True, methods=['post'], url_path='submit')
    def submit(self, request, pk=None):
        """
        Soumettre un workflow pour approbation.
        Transition : DRAFT → SUBMITTED
        """
        workflow = self.get_object()

        if workflow.workflow_status != ApprovalWorkflow.WorkflowStatus.DRAFT:
            return Response(
                {'error': {'code': 'bad_request',
                           'message': 'Seuls les workflows en brouillon peuvent être soumis.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        workflow.workflow_status = ApprovalWorkflow.WorkflowStatus.SUBMITTED
        workflow.submitted_by = request.user
        workflow.submitted_at = timezone.now()
        workflow.save(update_fields=['workflow_status', 'submitted_by', 'submitted_at'])

        return Response(ApprovalWorkflowSerializer(workflow).data)

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        """
        Approuver un workflow soumis.
        Transition : SUBMITTED → APPROVED
        Body (optionnel) : { approver_comment, unit_chief_comment }
        """
        workflow = self.get_object()

        if workflow.workflow_status != ApprovalWorkflow.WorkflowStatus.SUBMITTED:
            return Response(
                {'error': {'code': 'bad_request',
                           'message': 'Seuls les workflows soumis peuvent être approuvés.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        workflow.workflow_status = ApprovalWorkflow.WorkflowStatus.APPROVED
        workflow.approver = request.user
        workflow.approved_at = timezone.now()
        workflow.approver_comment = request.data.get('approver_comment', workflow.approver_comment)
        workflow.unit_chief_comment = request.data.get('unit_chief_comment', workflow.unit_chief_comment)
        workflow.save(update_fields=[
            'workflow_status', 'approver', 'approved_at',
            'approver_comment', 'unit_chief_comment',
        ])

        return Response(ApprovalWorkflowSerializer(workflow).data)

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        """
        Rejeter un workflow soumis avec un motif obligatoire.
        Transition : SUBMITTED → REJECTED
        Body : { approver_comment (motif obligatoire) }
        """
        workflow = self.get_object()

        if workflow.workflow_status != ApprovalWorkflow.WorkflowStatus.SUBMITTED:
            return Response(
                {'error': {'code': 'bad_request',
                           'message': 'Seuls les workflows soumis peuvent être rejetés.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reason = request.data.get('approver_comment', '').strip()
        if not reason:
            return Response(
                {'error': {'code': 'bad_request',
                           'message': 'Un motif de rejet est obligatoire (champ approver_comment).'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        workflow.workflow_status = ApprovalWorkflow.WorkflowStatus.REJECTED
        workflow.approver = request.user
        workflow.rejected_at = timezone.now()
        workflow.approver_comment = reason
        workflow.save(update_fields=[
            'workflow_status', 'approver', 'rejected_at', 'approver_comment',
        ])

        return Response(ApprovalWorkflowSerializer(workflow).data)

    @action(detail=False, methods=['get'], url_path='pending')
    def pending(self, request):
        """
        Liste des workflows en attente d'approbation (SUBMITTED).
        Accessible aux approbateurs et chefs d'unité.
        """
        if not (request.user.is_admin
                or request.user.has_role('APPROVER')
                or request.user.has_role('UNIT_CHIEF')):
            return Response(
                {'error': {'code': 'forbidden', 'message': 'Accès refusé.'}},
                status=status.HTTP_403_FORBIDDEN,
            )

        pending_qs = ApprovalWorkflow.objects.filter(
            workflow_status=ApprovalWorkflow.WorkflowStatus.SUBMITTED
        ).select_related('submitted_by', 'content_type').order_by('submitted_at')

        serializer = ApprovalWorkflowSerializer(pending_qs, many=True)
        return Response({'count': pending_qs.count(), 'results': serializer.data})
