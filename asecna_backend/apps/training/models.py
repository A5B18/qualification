"""
App training — Modèles pour formations, cours, stages et spécialités.

Hiérarchie :
  Specialty → Training (qualification EAMAC ou non) → Course (e-learning)
  Training  → Internship (stage qualifiant ou non qualifiant)
"""

import logging

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class Specialty(models.Model):
    """Spécialité technique d'un agent (ex: Contrôle aérien, Météo, Télécom…)."""

    code        = models.CharField(max_length=20, unique=True, verbose_name=_('Code'))
    name        = models.CharField(max_length=100, verbose_name=_('Nom'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    is_active   = models.BooleanField(default=True)

    class Meta:
        db_table            = 'training_specialty'
        verbose_name        = _('Spécialité')
        verbose_name_plural = _('Spécialités')
        ordering = ['code']

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


class Training(models.Model):
    """
    Formation (stage qualifiant EAMAC ou formation interne non qualifiante).
    """

    class TrainingType(models.TextChoices):
        QUALIFYING     = 'QUALIFYING',     _('Qualifiante (EAMAC)')
        NON_QUALIFYING = 'NON_QUALIFYING', _('Non qualifiante')
        ELEARNING      = 'ELEARNING',      _('E-learning')
        WORKSHOP       = 'WORKSHOP',       _('Atelier')

    specialty   = models.ForeignKey(
        Specialty, on_delete=models.SET_NULL, null=True,
        related_name='trainings', verbose_name=_('Spécialité'),
    )
    title       = models.CharField(max_length=200, verbose_name=_('Intitulé'))
    training_type = models.CharField(max_length=20, choices=TrainingType.choices,
                                     verbose_name=_('Type'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    duration_days = models.PositiveIntegerField(default=0, verbose_name=_('Durée (jours)'))
    passing_score = models.PositiveSmallIntegerField(
        default=70, verbose_name=_('Score de réussite'),
        help_text=_('70 pour formations standard, 80 pour qualifications EAMAC')
    )
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table            = 'training_training'
        verbose_name        = _('Formation')
        verbose_name_plural = _('Formations')

    def __str__(self) -> str:
        return f"{self.title} [{self.training_type}]"


class Course(models.Model):
    """Cours e-learning déposé par un instructeur."""

    training    = models.ForeignKey(Training, on_delete=models.CASCADE,
                                    related_name='courses', verbose_name=_('Formation'))
    instructor  = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='courses_taught', verbose_name=_('Instructeur'),
    )
    title       = models.CharField(max_length=200, verbose_name=_('Titre'))
    content     = models.TextField(verbose_name=_('Contenu'))
    file        = models.FileField(upload_to='courses/', null=True, blank=True,
                                   verbose_name=_('Fichier'))
    order       = models.PositiveSmallIntegerField(default=0, verbose_name=_('Ordre'))
    is_published = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'training_course'
        ordering = ['training', 'order']

    def __str__(self) -> str:
        return f"{self.training.title} — {self.title}"


class Internship(models.Model):
    """Stage pratique (qualifiant ou non qualifiant)."""

    class InternshipType(models.TextChoices):
        QUALIFYING     = 'QUALIFYING',     _('Qualifiant')
        NON_QUALIFYING = 'NON_QUALIFYING', _('Non qualifiant')

    agent       = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='internships', verbose_name=_('Agent'),
    )
    training    = models.ForeignKey(Training, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='internships')
    internship_type = models.CharField(max_length=20, choices=InternshipType.choices)
    location    = models.CharField(max_length=100, blank=True)
    start_date  = models.DateField()
    end_date    = models.DateField()
    is_passed   = models.BooleanField(null=True, blank=True)  # NULL = en cours
    report      = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'training_internship'

    def __str__(self) -> str:
        return f"Stage {self.internship_type} de {self.agent} ({self.start_date})"


class QualificationMaintenance(models.Model):
    """
    Contrôle de maintien de qualification (tous les 2 ans, score >= 70/100).

    Règle métier :
      - Qualification initiale : 80/100
      - Maintien tous les 2 ans : 70/100 minimum
      - Si FAILED → agent passe à SUSPENDED jusqu'à re-qualification
    """

    class MaintenanceStatus(models.TextChoices):
        PENDING = 'PENDING', _('En attente')
        PASSED  = 'PASSED',  _('Réussi')
        FAILED  = 'FAILED',  _('Echoué')
        WAIVED  = 'WAIVED',  _('Dispensé (décision chef d\'unité)')

    # Seuil minimal de maintien (règle métier)
    MAINTENANCE_SCORE = 70

    agent       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='qualification_maintenances',
        verbose_name=_('Agent'),
    )
    training    = models.ForeignKey(
        Training, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='maintenances',
        verbose_name=_('Formation de maintien'),
    )
    due_date    = models.DateField(
        verbose_name=_('Date d\'échéance'),
        help_text=_('2 ans après la qualification ou le dernier maintien réussi.'),
    )
    score       = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        verbose_name=_('Score (/100)'),
    )
    maintenance_status = models.CharField(
        max_length=20,
        choices=MaintenanceStatus.choices,
        default=MaintenanceStatus.PENDING,
        verbose_name=_('Statut'),
    )
    evaluated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='maintenances_evaluated',
        verbose_name=_('Évalué par'),
    )
    evaluated_at = models.DateTimeField(null=True, blank=True)
    notes       = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

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
          - score >= 70 → PASSED (agent reste QUALIFIED)
          - score < 70  → FAILED (agent passe à SUSPENDED)

        Les deux écritures vont ensemble : un contrôle marqué FAILED sans la
        suspension qui l'accompagne laisserait un agent non qualifié en
        service. D'où la transaction.
        """
        self.score = score
        self.evaluated_by = evaluator
        self.evaluated_at = timezone.now()
        self.notes = notes
        passed = score >= self.MAINTENANCE_SCORE
        self.maintenance_status = (
            self.MaintenanceStatus.PASSED if passed else self.MaintenanceStatus.FAILED
        )

        with transaction.atomic():
            self.save()
            self._apply_status_to_agent(passed)

    def _apply_status_to_agent(self, passed: bool) -> None:
        """
        Répercute le résultat sur le parcours de l'agent.

        Un agent sans profil (compte purement technique) n'a pas de parcours à
        mettre à jour : c'est le seul cas toléré, et il est nommé. Auparavant,
        un `except Exception: pass` avalait aussi les erreurs de base de
        données — un contrôle pouvait être enregistré FAILED sans que l'agent
        soit suspendu, sans trace ni message.
        """
        from apps.accounts.models import AgentProfile, AgentStatus

        try:
            profile = self.agent.agent_profile
        except AgentProfile.DoesNotExist:
            logger.info(
                "Maintien de qualification %s : l'agent %s n'a pas de profil de "
                "parcours, aucun statut à mettre à jour.",
                self.pk, self.agent_id,
            )
            return

        if passed:
            # Un maintien réussi ne requalifie que l'agent suspendu ;
            # les autres statuts de parcours ne sont pas concernés.
            if profile.status == AgentStatus.SUSPENDED:
                profile.status = AgentStatus.QUALIFIED
                profile.save(update_fields=['status'])
        else:
            profile.status = AgentStatus.SUSPENDED
            profile.save(update_fields=['status'])

    def __str__(self) -> str:
        score_str = f' — {self.score}/100' if self.score is not None else ''
        return f'Maintien QF {self.agent} (échéance: {self.due_date}){score_str} [{self.maintenance_status}]'
