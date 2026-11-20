"""
Views pour l'app workflows — Pipeline d'approbation générique.

Actions disponibles :
  POST .../submit/   → soumettre un workflow (DRAFT → SUBMITTED)
  POST .../approve/  → approuver (SUBMITTED → APPROVED)
  POST .../reject/   → rejeter avec motif (SUBMITTED → REJECTED)
"""

from django.apps import apps as django_apps
from django.contrib.contenttypes.prefetch import GenericPrefetch
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from core.permissions import IsApproverOrUnitChief
from .models import ApprovalWorkflow
from .serializers import ApprovalWorkflowSerializer


def _target_querysets():
    """
    Querysets de préchargement des objets soumis, un par module raccordé.

    `GenericPrefetch` (Django 5.0) permet d'associer un queryset à chaque
    modèle visé par une clé générique. Sans lui, le serializer résolvait
    `content_object` ligne par ligne, puis repartait en base pour l'agent et
    l'examen de chaque objet : le registre consommait une à deux requêtes par
    ligne affichée.

    Les modèles sont résolus par leur étiquette, comme `MODULE_LABELS` le fait
    déjà, pour que l'app `workflows` n'importe pas ses modules consommateurs.
    """
    extra_select_related = {
        'evaluations.examsession': ('agent', 'exam'),
        'reports.report': ('agent', 'created_by'),
        'mentoring.mentoringrecord': ('agent', 'mentor'),
    }
    querysets = []
    for label, relations in extra_select_related.items():
        try:
            model = django_apps.get_model(label)
        except LookupError:  # pragma: no cover - module retiré du projet
            continue
        querysets.append(model.objects.select_related(*relations))
    return querysets


class ApprovalWorkflowViewSet(viewsets.ModelViewSet):
    """
    CRUD + actions du pipeline d'approbation.

    Registre transversal des decisions : une ligne par objet soumis, quel que
    soit son module d'origine. Alimente par `apps.workflows.services`, appele
    par les rapports, les fiches de mentorat et les corrections d'examen.

    Chaque module garde sa propre machine a etats ; ce registre sert a voir au
    meme endroit tout ce qui attend une decision, et a retracer qui a decide
    quoi.

    Filtres disponibles (query params) :
      ?workflow_status=DRAFT|SUBMITTED|APPROVED|REJECTED
      ?module=report|mentoringrecord|examsession
      ?content_type=<id>
      ?object_id=<id>

    Un agent sans role de decision ne voit que ses propres soumissions.
    """
    serializer_class = ApprovalWorkflowSerializer
    # Jamais consulte a l'execution (get_queryset ci-dessous le remplace) ;
    # present pour que drf-spectacular type le parametre de chemin `id` en
    # entier. Depuis que get_queryset() lit `request.user` pour cloisonner, il
    # echoue hors requete, et le schema declarait `id` comme une chaine.
    queryset = ApprovalWorkflow.objects.none()

    def get_queryset(self):
        user = self.request.user
        qs = ApprovalWorkflow.objects.select_related(
            'submitted_by', 'approver', 'unit_chief', 'content_type',
        # `content_object` est une cle generique : sans ce prefetch, le
        # serializer declenche une requete par ligne pour resoudre l'objet,
        # puis une autre pour son agent et, pour une session, son examen.
        ).prefetch_related(
            GenericPrefetch('content_object', _target_querysets()),
        ).order_by('-created_at')

        # Cloisonnement. Le registre servait l'integralite de la table a tout
        # utilisateur authentifie : un agent y lisait les soumissions de ses
        # collegues. Tant qu'il n'etait alimente que par `seed_demo` la fuite
        # restait theorique ; elle ne l'est plus une fois les modules
        # raccordes.
        if not (user.is_admin or user.has_any_role('APPROVER', 'UNIT_CHIEF')):
            qs = qs.filter(submitted_by=user)

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

        # `?module=report|mentoringrecord|examsession` : l'ecran d'approbation
        # filtre par type d'objet sans avoir a connaitre les identifiants de
        # ContentType.
        module = self.request.query_params.get('module')
        if module:
            qs = qs.filter(content_type__model=module)

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
                or request.user.has_any_role('APPROVER', 'UNIT_CHIEF')):
            return Response(
                {'error': {'code': 'forbidden', 'message': 'Accès refusé.'}},
                status=status.HTTP_403_FORBIDDEN,
            )

        pending_qs = (ApprovalWorkflow.objects
                      .filter(workflow_status=ApprovalWorkflow.WorkflowStatus.SUBMITTED)
                      .select_related('submitted_by', 'approver', 'unit_chief',
                                      'content_type')
                      .prefetch_related('content_object')
                      .order_by('submitted_at'))

        module = request.query_params.get('module')
        if module:
            pending_qs = pending_qs.filter(content_type__model=module)

        serializer = ApprovalWorkflowSerializer(pending_qs, many=True)
        return Response({'count': pending_qs.count(), 'results': serializer.data})
