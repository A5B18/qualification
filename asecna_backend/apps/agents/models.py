"""
App agents — Compétences, certifications et indicateurs de performance.

Complète AgentProfile avec des données plus granulaires sur les acquis.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class AgentSkill(models.Model):
    """Compétence technique acquise par un agent."""

    agent       = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='skills', verbose_name=_('Agent'),
    )
    name        = models.CharField(max_length=100, verbose_name=_('Nom de la compétence'))
    level       = models.PositiveSmallIntegerField(
        default=1, verbose_name=_('Niveau (1-5)'),
        help_text=_('1 = débutant, 5 = expert'),
    )
    acquired_at = models.DateField(null=True, blank=True)
    notes       = models.TextField(blank=True)

    class Meta:
        db_table = 'agents_skill'

    def __str__(self) -> str:
        return f"{self.agent} — {self.name} (niv. {self.level})"


class AgentCertification(models.Model):
    """Certification officielle obtenue par un agent."""

    agent           = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='certifications',
    )
    name            = models.CharField(max_length=200, verbose_name=_('Certification'))
    issuing_body    = models.CharField(max_length=100, blank=True, verbose_name=_('Organisme'))
    issue_date      = models.DateField(verbose_name=_('Date d\'obtention'))
    expiry_date     = models.DateField(null=True, blank=True, verbose_name=_('Date d\'expiration'))
    certificate_file = models.FileField(upload_to='certifications/', null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'agents_certification'
        ordering = ['-issue_date']

    def __str__(self) -> str:
        return f"{self.agent} — {self.name}"


class PerformanceIndicator(models.Model):
    """Indicateur de performance annuel d'un agent."""

    agent       = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='performance_indicators',
    )
    year        = models.PositiveSmallIntegerField(verbose_name=_('Année'))
    score       = models.DecimalField(max_digits=5, decimal_places=2,
                                      verbose_name=_('Score global /100'))
    evaluator   = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='performance_evaluations',
    )
    comments    = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'agents_performance'
        constraints = [
            models.UniqueConstraint(fields=['agent', 'year'], name='unique_perf_per_agent_year')
        ]

    def __str__(self) -> str:
        return f"Perf {self.year} de {self.agent} : {self.score}/100"
