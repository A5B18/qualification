"""Views pour reports."""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.utils import timezone

from core.permissions import IsApproverOrUnitChief, IsAdministrator
from apps.workflows import services as workflows
from .models import Report
from .serializers import ReportSerializer


class ReportViewSet(viewsets.ModelViewSet):
    serializer_class = ReportSerializer
    # Jamais consulte a l'execution (get_queryset ci-dessous le remplace) ;
    # present pour que drf-spectacular type le parametre de chemin `id`
    # en entier au lieu de le deduire d'un get_queryset() qui echoue
    # hors requete.
    queryset = Report.objects.none()

    def get_queryset(self):
        user = self.request.user
        base = Report.objects.select_related('agent', 'created_by', 'approver', 'unit_chief')
        if user.is_admin or user.has_role('UNIT_CHIEF') or user.has_role('APPROVER'):
            qs = base.all()
        else:
            qs = base.filter(agent=user)
        # Filtres ?agent= / ?report_status= utilises par le frontend
        agent_id = self.request.query_params.get('agent')
        if agent_id:
            qs = qs.filter(agent_id=agent_id)
        report_status = self.request.query_params.get('report_status')
        if report_status:
            qs = qs.filter(report_status=report_status)
        return qs.order_by('-created_at', '-id')

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        if self.action in ('approve', 'reject'):
            return [IsAuthenticated(), IsApproverOrUnitChief()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        report = self.get_object()
        if report.report_status != Report.ReportStatus.DRAFT:
            return Response({'error': {'code': 'bad_request', 'message': 'Rapport non en brouillon.'}},
                            status=status.HTTP_400_BAD_REQUEST)
        # La transition metier et son inscription au registre d'approbation
        # vont ensemble : si l'une echoue, l'autre ne doit pas rester.
        with transaction.atomic():
            report.report_status = Report.ReportStatus.SUBMITTED
            report.submitted_at = timezone.now()
            report.save()
            workflows.record_submission(report, submitted_by=request.user)
        return Response(ReportSerializer(report).data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        report = self.get_object()
        if report.report_status != Report.ReportStatus.SUBMITTED:
            return Response({'error': {'code': 'bad_request', 'message': 'Rapport non soumis.'}},
                            status=status.HTTP_400_BAD_REQUEST)
        opinion = request.data.get('opinion', '')
        with transaction.atomic():
            report.approver_opinion = opinion
            report.report_status = Report.ReportStatus.APPROVED
            report.approved_at = timezone.now()
            report.approver = request.user
            report.save()
            workflows.record_approval(report, approver=request.user, comment=opinion)
        return Response(ReportSerializer(report).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        report = self.get_object()
        # Seul un rapport soumis peut etre rejete (le controle manquait :
        # on pouvait rejeter un brouillon ou un rapport deja approuve)
        if report.report_status != Report.ReportStatus.SUBMITTED:
            return Response({'error': {'code': 'bad_request', 'message': 'Rapport non soumis.'}},
                            status=status.HTTP_400_BAD_REQUEST)
        opinion = request.data.get('opinion', '')
        with transaction.atomic():
            report.approver = request.user
            report.approver_opinion = opinion
            report.report_status = Report.ReportStatus.REJECTED
            report.save()
            workflows.record_rejection(report, approver=request.user, reason=opinion)
        return Response(ReportSerializer(report).data)
