"""
App training — Ajout du modèle QualificationMaintenance.

Règle métier (cahier des charges) :
  - Qualification initiale : score requis 80/100 (via ExamSession + Training.passing_score=80)
  - Maintien de qualification : tous les 2 ans, score minimum 70/100
  - Si le maintien échoue → statut agent passe à SUSPENDED jusqu'à re-qualification
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from .models import Training


class QualificationMaintenance(models.Model):
    """
    Contrôle de maintien de qualification (tous les 2 ans, score >= 70/100).

    Invariant :
      - Créé automatiquement 2 ans après la qualification initiale (ou le dernier maintien réussi)
      - Si FAILED → agent passe à SUSPENDED jusqu'à une nouvelle session réussie
    """

    class MaintenanceStatus(models.TextChoices):
        PENDING  = 'PENDING',  _('En attente')
        PASSED   = 'PASSED',   _('Réussi')
        FAILED   = 'FAILED',   _('Échoué')
        WAIVED   = 'WAIVED',   _('Dispensé (décision chef d\'unité)')

    # Seuil minimal de maintien (règle métier)
    MAINTENANCE_SCORE = 70

    agent           = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='qualification_maintenances',
        verbose_name=_('Agent'),
    )
    training        = models.ForeignKey(
        Training,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='maintenances',
        verbose_name=_('Formation de maintien'),
    )
    due_date        = models.DateField(
        verbose_name=_('Date d\'échéance'),
        help_text=_('Date à laquelle le maintien doit être effectué (2 ans après qualification).'),
    )
    score           = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        verbose_name=_('Score obtenu (/100)'),
    )
    maintenance_status = models.CharField(
        max_length=20,
        choices=MaintenanceStatus.choices,
        default=MaintenanceStatus.PENDING,
        verbose_name=_('Statut'),
    )
    evaluated_by    = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='maintenances_evaluated',
        verbose_name=_('Évalué par'),
    )
    evaluated_at    = models.DateTimeField(null=True, blank=True)
    notes           = models.TextField(blank=True, verbose_name=_('Notes'))
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'training_qualification_maintenance'
        verbose_name = _('Maintien de qualification')
        verbose_name_plural = _('Maintiens de qualification')
        ordering = ['-due_date']
        indexes = [
            models.Index(fields=['agent', 'maintenance_status'], name='idx_maint_status'),
            models.Index(fields=['due_date'], name='idx_maint_due'),
        ]

    @property
    def score_passed(self) -> bool:
        """True si le score est suffisant pour le maintien (>= 70/100)."""
        return self.score is not None and self.score >= self.MAINTENANCE_SCORE

    def finalize(self, evaluator, score: float, notes: str = ''):
        """
        Enregistre le résultat du contrôle de maintien.
        Met à jour le statut de l'agent selon les règles métier.
        """
        from django.utils import timezone
        from apps.accounts.models import AgentStatus

        self.score = score
        self.evaluated_by = evaluator
        self.evaluated_at = timezone.now()
        self.notes = notes

        if score >= self.MAINTENANCE_SCORE:
            self.maintenance_status = self.MaintenanceStatus.PASSED
            # S'assurer que l'agent est bien QUALIFIED
            try:
                profile = self.agent.agent_profile
                if profile.status == AgentStatus.SUSPENDED:
                    profile.status = AgentStatus.QUALIFIED
                    profile.save(update_fields=['status'])
            except Exception:
                pass
        else:
            self.maintenance_status = self.MaintenanceStatus.FAILED
            # Suspendre l'agent en attendant re-qualification
            try:
                profile = self.agent.agent_profile
                profile.status = AgentStatus.SUSPENDED
                profile.save(update_fields=['status'])
            except Exception:
                pass

        self.save()

    def __str__(self) -> str:
        score_str = f' — {self.score}/100' if self.score is not None else ''
        return (
            f'Maintien qualification {self.agent} '
            f'(échéance: {self.due_date}){score_str} [{self.maintenance_status}]'
        )
