"""
App reports — 3 types de rapports exportables.

Types :
  1. PROBATION  → Rapport de fin de période d'essai
  2. MENTORING  → Rapport de mentorat
  3. ASSESSMENT → Bilan périodique de l'agent

Workflow : DRAFT → SUBMITTED → APPROVED (même pipeline que workflows)
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class Report(models.Model):
    """Rapport documentaire généré pour un agent."""

    class ReportType(models.TextChoices):
        PROBATION  = 'PROBATION',  _('Rapport période d\'essai')
        MENTORING  = 'MENTORING',  _('Rapport de mentorat')
        ASSESSMENT = 'ASSESSMENT', _('Bilan périodique')

    class ReportStatus(models.TextChoices):
        DRAFT     = 'DRAFT',     _('Brouillon')
        SUBMITTED = 'SUBMITTED', _('Soumis')
        APPROVED  = 'APPROVED',  _('Approuvé')
        REJECTED  = 'REJECTED',  _('Rejeté')

    report_type = models.CharField(max_length=20, choices=ReportType.choices)
    agent       = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='reports', verbose_name=_('Agent concerné'),
    )
    created_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='reports_created',
    )
    approver    = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reports_to_approve',
    )
    unit_chief  = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reports_to_sign',
    )

    title       = models.CharField(max_length=200)
    content     = models.TextField(verbose_name=_('Corps du rapport'))
    conclusion  = models.TextField(blank=True)
    approver_opinion  = models.TextField(blank=True)
    unit_chief_opinion = models.TextField(blank=True)

    report_status = models.CharField(
        max_length=20, choices=ReportStatus.choices, default=ReportStatus.DRAFT,
    )

    # Fichier exporté (PDF généré)
    file        = models.FileField(upload_to='reports/', null=True, blank=True)

    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at  = models.DateTimeField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        db_table            = 'reports_report'
        verbose_name        = _('Rapport')
        verbose_name_plural = _('Rapports')
        indexes = [
            models.Index(fields=['agent', 'report_type'], name='idx_report_agent_type'),
            models.Index(fields=['report_status'],        name='idx_report_status'),
        ]

    def __str__(self) -> str:
        return f"[{self.report_type}] {self.title} — {self.agent}"
