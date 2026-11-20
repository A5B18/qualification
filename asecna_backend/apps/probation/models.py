"""
Modèle de période d'essai.

Règles métier :
  - 2 tentatives maximum par agent (jamais plus)
  - Durée de chaque tentative : 3 mois (90 jours)
  - Note minimale pour réussir : 70/100
  - Si la 2ème tentative échoue → agent non retenu (statut RETIRED ou SUSPENDED)
  - La création d'une 3ème tentative est bloquée au niveau du modèle
  - Évaluation déclenchée J-14 avant la fin de la période
"""

from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings
import datetime


class ProbationPeriod(models.Model):
    """
    Période d'essai d'un agent ASECNA.

    Contrainte centrale : max 2 tentatives par agent (attempt_number : 1 ou 2).
    Le champ is_passed est NULL tant que la période est en cours.
    """

    class ProbationStatus(models.TextChoices):
        IN_PROGRESS = 'IN_PROGRESS', _('En cours')
        PASSED      = 'PASSED',      _('Réussie')
        FAILED      = 'FAILED',      _('Échouée')
        EXTENDED    = 'EXTENDED',    _('Prolongée')   # Si renewal avant fin
        ABANDONED   = 'ABANDONED',   _('Abandonnée')

    agent           = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='probation_periods',
        verbose_name=_('Agent'),
    )
    attempt_number  = models.PositiveSmallIntegerField(
        verbose_name=_('Numéro de tentative'),
        help_text=_('1 pour la première tentative, 2 pour la deuxième et dernière')
    )
    start_date      = models.DateField(verbose_name=_('Date de début'))
    end_date        = models.DateField(verbose_name=_('Date de fin prévue'))
    actual_end_date = models.DateField(
        null=True, blank=True, verbose_name=_('Date de fin réelle')
    )
    probation_status = models.CharField(
        max_length=20,
        choices=ProbationStatus.choices,
        default=ProbationStatus.IN_PROGRESS,
        verbose_name=_('Statut'),
    )

    # ── Score d'évaluation ─────────────────────────────────────────────────────
    # Règle métier : note minimale 70/100 pour valider la période d'essai
    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('Note (/100)'),
        help_text=_('Note obtenue à l\'évaluation de fin de période. Minimum 70/100 pour réussir.'),
    )
    # Observations du chef d'unité à la fin de la période
    unit_chief_comment = models.TextField(blank=True, verbose_name=_("Avis chef d'unité"))
    mentor_comment     = models.TextField(blank=True, verbose_name=_('Avis mentor'))

    evaluated_by    = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='probation_evaluations',
        verbose_name=_('Évalué par'),
    )
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table            = 'probation_period'
        verbose_name        = _('Période d\'essai')
        verbose_name_plural = _('Périodes d\'essai')
        ordering = ['agent', 'attempt_number']
        constraints = [
            # Règle métier : max 2 tentatives par agent
            models.CheckConstraint(
                check=models.Q(attempt_number__in=[1, 2]),
                name='probation_attempt_max_2',
            ),
            # Unicité de (agent, attempt_number)
            models.UniqueConstraint(
                fields=['agent', 'attempt_number'],
                name='unique_probation_attempt_per_agent',
            ),
        ]
        indexes = [
            models.Index(fields=['agent', 'probation_status'], name='idx_probation_status'),
        ]

    # -------------------------------------------------------------------------
    # Validation métier
    # -------------------------------------------------------------------------

    # Seuil minimal de réussite (règle métier)
    PASSING_SCORE = 70

    def clean(self):
        """
        Validation centrale :
        1. Bloquer une 3ème tentative (impossible si 2 existent déjà)
        2. Bloquer attempt_number=2 si attempt_number=1 n'est pas encore finalisée
        3. La date de fin doit être ~ 3 mois après le début
        4. Si un score est fourni et que le statut est PASSED, le score doit être >= 70/100
        """
        super().clean()

        if self.attempt_number == 2:
            first_attempt = ProbationPeriod.objects.filter(
                agent=self.agent, attempt_number=1
            ).exclude(pk=self.pk).first()

            if not first_attempt:
                raise ValidationError(
                    _("Impossible de créer une 2ème tentative sans 1ère tentative enregistrée.")
                )
            if first_attempt.probation_status == self.ProbationStatus.IN_PROGRESS:
                raise ValidationError(
                    _("La 1ère tentative est encore en cours. Finalisez-la avant d'en créer une 2ème.")
                )
            if first_attempt.probation_status == self.ProbationStatus.PASSED:
                raise ValidationError(
                    _("La 1ère tentative a été réussie. Une 2ème tentative n'est pas nécessaire.")
                )

        # Durée approximativement de 3 mois (entre 80 et 100 jours)
        if self.start_date and self.end_date:
            duration = (self.end_date - self.start_date).days
            if not (80 <= duration <= 100):
                raise ValidationError(
                    _(
                        f"La durée de la période d'essai ({duration} jours) doit être "
                        "approximativement de 3 mois (80 à 100 jours)."
                    )
                )

        # Règle métier : score minimum 70/100 obligatoire pour PASSED
        if self.probation_status == self.ProbationStatus.PASSED:
            if self.score is None:
                raise ValidationError(
                    _("Un score est obligatoire pour valider une période d'essai comme réussie.")
                )
            if self.score < self.PASSING_SCORE:
                raise ValidationError(
                    _(f"Le score ({self.score}/100) est inférieur au minimum requis ({self.PASSING_SCORE}/100). "
                      "La période d'essai ne peut pas être marquée comme réussie.")
                )

        # Cohérence : si score < 70 → ne peut pas être PASSED
        if self.score is not None and self.score < self.PASSING_SCORE:
            if self.probation_status == self.ProbationStatus.PASSED:
                raise ValidationError(
                    _(f"Score insuffisant ({self.score}/100). Minimum requis : {self.PASSING_SCORE}/100.")
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    # -------------------------------------------------------------------------
    # Propriétés utilitaires
    # -------------------------------------------------------------------------

    @property
    def is_last_attempt(self) -> bool:
        """True si c'est la 2ème tentative (dernière autorisée)."""
        return self.attempt_number == 2

    @property
    def is_renewable(self) -> bool:
        """True si une 2ème tentative est possible (1ère échouée, pas encore de 2ème)."""
        return (
            self.attempt_number == 1
            and self.probation_status == self.ProbationStatus.FAILED
            and not ProbationPeriod.objects.filter(agent=self.agent, attempt_number=2).exists()
        )

    @property
    def score_passed(self) -> bool:
        """True si le score est suffisant pour réussir (>= 70/100)."""
        return self.score is not None and self.score >= self.PASSING_SCORE

    @property
    def evaluation_due_date(self) -> datetime.date:
        """
        Date à laquelle l'évaluation doit être déclenchée.
        Règle métier : J-14 avant la date de fin prévue.
        """
        return self.end_date - datetime.timedelta(days=14)

    @property
    def evaluation_is_due(self) -> bool:
        """
        True si l'évaluation doit être déclenchée aujourd'hui ou est déjà en retard.
        (= on est à J-14 ou moins avant la fin, et la période est encore en cours)
        """
        return (
            self.probation_status == self.ProbationStatus.IN_PROGRESS
            and timezone.localdate() >= self.evaluation_due_date
        )

    @property
    def days_until_evaluation(self) -> int:
        """
        Nombre de jours restants avant le déclenchement de l'évaluation.
        Négatif si l'évaluation est en retard.
        """
        return (self.evaluation_due_date - timezone.localdate()).days

    def __str__(self) -> str:
        score_str = f" — {self.score}/100" if self.score is not None else ""
        return (
            f"Essai #{self.attempt_number} de {self.agent} — "
            f"{self.start_date} → {self.end_date} [{self.probation_status}]{score_str}"
        )
