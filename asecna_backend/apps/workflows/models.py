"""
App workflows — Modèle d'approbation générique.

Pipeline : DRAFT → SUBMITTED → APPROVED / REJECTED
Utilisé par : corrections d'examen, rapports, fiches mentorat.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class ApprovalWorkflow(models.Model):
    """
    Workflow d'approbation générique (via GenericForeignKey).
    Peut être attaché à n'importe quel objet (rapport, correction, etc.)
    """

    class WorkflowStatus(models.TextChoices):
        DRAFT     = 'DRAFT',     _('Brouillon')
        SUBMITTED = 'SUBMITTED', _('Soumis')
        APPROVED  = 'APPROVED',  _('Approuvé')
        REJECTED  = 'REJECTED',  _('Rejeté')

    # Lien générique vers l'objet soumis à approbation
    content_type    = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id       = models.PositiveIntegerField()
    content_object  = GenericForeignKey('content_type', 'object_id')

    submitted_by    = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='workflows_submitted',
    )
    approver        = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='workflows_to_approve',
    )
    unit_chief      = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='workflows_to_sign',
    )

    workflow_status = models.CharField(
        max_length=20, choices=WorkflowStatus.choices, default=WorkflowStatus.DRAFT,
    )
    approver_comment  = models.TextField(blank=True, verbose_name=_('Avis approbateur'))
    unit_chief_comment = models.TextField(blank=True, verbose_name=_('Avis chef d\'unité'))

    submitted_at    = models.DateTimeField(null=True, blank=True)
    approved_at     = models.DateTimeField(null=True, blank=True)
    rejected_at     = models.DateTimeField(null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'workflows_approval'
        indexes  = [models.Index(fields=['content_type', 'object_id'], name='idx_workflow_object')]
        constraints = [
            # Un objet metier n'a qu'une ligne de registre : c'est ce qui rend
            # `apps.workflows.services` idempotent (une resoumission met la
            # ligne a jour au lieu d'en empiler une seconde) et ce qui permet
            # de remonter du registre vers l'objet sans ambiguite.
            models.UniqueConstraint(
                fields=['content_type', 'object_id'],
                name='unique_workflow_per_object',
            ),
        ]

    def __str__(self) -> str:
        return f"Workflow [{self.workflow_status}] — {self.content_object}"
