"""
Modèle de mentorat.

Flux :
  1. Mentor crée la fiche (DRAFT)
  2. Mentor remplit les observations périodiques
  3. Mentor soumet au chef d'unité (SUBMITTED)
  4. Chef d'unité approuve ou rejette (APPROVED / REJECTED)
"""

from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class MentoringRecord(models.Model):
    """
    Fiche de mentorat entre un agent (mentoré) et son mentor.
    Un agent ne peut avoir qu'une fiche de mentorat active à la fois.
    """

    class MentoringStatus(models.TextChoices):
        DRAFT     = 'DRAFT',     _('Brouillon')
        SUBMITTED = 'SUBMITTED', _('Soumise au chef d\'unité')
        APPROVED  = 'APPROVED',  _('Approuvée')
        REJECTED  = 'REJECTED',  _('Rejetée')
        COMPLETED = 'COMPLETED', _('Terminée')

    # Participants
    agent           = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mentoring_records_as_agent',
        verbose_name=_('Agent mentoré'),
    )
    mentor          = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='mentoring_records_as_mentor',
        verbose_name=_('Mentor'),
    )
    unit_chief      = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='mentoring_records_as_chief',
        verbose_name=_('Chef d\'unité signataire'),
    )

    # Période
    start_date      = models.DateField(verbose_name=_('Date de début'))
    end_date        = models.DateField(null=True, blank=True, verbose_name=_('Date de fin'))

    # Contenu de la fiche
    objectives      = models.TextField(verbose_name=_('Objectifs de mentorat'))
    mentor_observations = models.TextField(blank=True, verbose_name=_('Observations du mentor'))
    mentor_opinion  = models.TextField(blank=True, verbose_name=_('Avis final du mentor'))
    unit_chief_opinion = models.TextField(blank=True, verbose_name=_('Avis du chef d\'unité'))

    # Workflow
    mentoring_status = models.CharField(
        max_length=20,
        choices=MentoringStatus.choices,
        default=MentoringStatus.DRAFT,
        verbose_name=_('Statut'),
    )
    submitted_at    = models.DateTimeField(null=True, blank=True, verbose_name=_('Soumise le'))
    approved_at     = models.DateTimeField(null=True, blank=True, verbose_name=_('Approuvée le'))

    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table            = 'mentoring_record'
        verbose_name        = _('Fiche de mentorat')
        verbose_name_plural = _('Fiches de mentorat')
        ordering = ['-created_at']
        constraints = [
            # Un agent ne peut avoir qu'une fiche active (DRAFT ou SUBMITTED)
            models.UniqueConstraint(
                fields=['agent'],
                condition=models.Q(mentoring_status__in=['DRAFT', 'SUBMITTED']),
                name='unique_active_mentoring_per_agent',
            ),
        ]
        indexes = [
            models.Index(fields=['agent', 'mentoring_status'], name='idx_mentoring_status'),
            models.Index(fields=['mentor'],                    name='idx_mentoring_mentor'),
        ]

    def clean(self):
        """Valider que le mentor et l'agent sont différents."""
        super().clean()
        if self.mentor and self.agent_id == self.mentor_id:
            raise ValidationError(_("Un agent ne peut pas être son propre mentor."))

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def submit(self, unit_chief):
        """Soumettre la fiche au chef d'unité."""
        from django.utils import timezone
        if self.mentoring_status != self.MentoringStatus.DRAFT:
            raise ValidationError(_("Seules les fiches en brouillon peuvent être soumises."))
        self.unit_chief = unit_chief
        self.mentoring_status = self.MentoringStatus.SUBMITTED
        self.submitted_at = timezone.now()
        self.save()

    def approve(self, opinion: str = ''):
        """Approuver la fiche (chef d'unité)."""
        from django.utils import timezone
        if self.mentoring_status != self.MentoringStatus.SUBMITTED:
            raise ValidationError(_("Seules les fiches soumises peuvent être approuvées."))
        self.unit_chief_opinion = opinion
        self.mentoring_status = self.MentoringStatus.APPROVED
        self.approved_at = timezone.now()
        self.save()

    def reject(self, opinion: str = ''):
        """Rejeter la fiche (chef d'unité)."""
        if self.mentoring_status != self.MentoringStatus.SUBMITTED:
            raise ValidationError(_("Seules les fiches soumises peuvent être rejetées."))
        self.unit_chief_opinion = opinion
        self.mentoring_status = self.MentoringStatus.REJECTED
        self.save()

    def __str__(self) -> str:
        return f"Mentorat {self.agent} par {self.mentor} [{self.mentoring_status}]"
