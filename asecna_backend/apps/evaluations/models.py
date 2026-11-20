"""
App evaluations — Modèles pour questions, examens, réponses et scores.

Workflow de correction (manuel par les évaluateurs) :
  1. Agent soumet ses réponses → session passe à SUBMITTED
  2. Évaluateur corrige réponse par réponse (Answer.evaluator_score)
  3. Évaluateur marque la session à PENDING_APPROVAL
  4. Chef d'unité approuve → GRADED (score officiel enregistré) ou REJECTED

Règle métier :
  - Toute question d'évaluation est un QCM : un énoncé, au moins deux options
    proposées, et une bonne réponse qui figure parmi ces options. Les formats
    « Vrai/Faux » et « réponse ouverte » ont été retirés (migration 0003) :
    une réponse libre ne peut pas être corrigée de façon reproductible, et le
    Vrai/Faux n'est qu'un QCM à deux options.
  - Score de réussité basé sur Training.passing_score (70 pour probabilité, 80 pour qualification)
  - Questions par catégories : GENERAL, TECHNICAL, UNIT_SPECIFIC
  - Niveaux de difficulté 1 à 5
"""

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.training.models import Training


class Question(models.Model):
    """
    Question d'examen — toujours un QCM.

    Invariants garantis par `clean()`, que le serializer applique après avoir
    normalisé les options :
      - au moins MIN_OPTIONS options non vides, au plus MAX_OPTIONS ;
      - aucun doublon parmi les options ;
      - `correct_answer` figure parmi les options.

    Sans ces invariants un QCM pouvait être enregistré sans aucune option :
    l'agent recevait un énoncé sans choix, et la correction n'avait plus de
    référence opposable.
    """

    class QuestionType(models.TextChoices):
        GENERAL        = 'GENERAL',        _('Généralités')
        TECHNICAL      = 'TECHNICAL',      _('Technique')
        UNIT_SPECIFIC  = 'UNIT_SPECIFIC',  _('Spécifique à l\'unité')

    class QuestionKind(models.TextChoices):
        """Un seul format d'évaluation : le QCM (cf. docstring du module)."""
        MCQ  = 'MCQ',  _('QCM (choix multiple)')

    #: Bornes du nombre de propositions d'un QCM.
    MIN_OPTIONS = 2
    MAX_OPTIONS = 6

    training        = models.ForeignKey(Training, on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='questions')
    question_type   = models.CharField(max_length=20, choices=QuestionType.choices)
    question_kind   = models.CharField(max_length=10, choices=QuestionKind.choices,
                                       default=QuestionKind.MCQ,
                                       verbose_name=_('Format'),
                                       help_text=_('QCM — seul format accepté.'))
    text            = models.TextField(verbose_name=_('Énoncé'))
    difficulty      = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name=_('Difficulté'), help_text=_('1 = facile, 5 = très difficile'),
    )
    correct_answer  = models.TextField(
        verbose_name=_('Bonne réponse'),
        help_text=_('Doit être l\'une des options proposées.'),
    )
    options         = models.JSONField(default=list, blank=True,
                                       verbose_name=_('Options (QCM)'))  # ["A", "B", "C", "D"]
    points          = models.PositiveSmallIntegerField(default=1, verbose_name=_('Points'))
    created_by      = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='questions_created',
    )
    is_active       = models.BooleanField(default=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'evaluations_question'
        indexes  = [models.Index(fields=['training', 'question_type', 'difficulty'],
                                 name='idx_question_lookup')]

    # ── Normalisation et contrôles du QCM ────────────────────────────────────

    @staticmethod
    def normalize_options(options) -> list:
        """
        Nettoie une liste d'options : espaces rognés, vides écartés.

        Le formulaire de composition propose quatre champs ; les deux derniers
        restent souvent vides et n'ont pas à rejoindre la base.
        """
        if not options:
            return []
        if isinstance(options, str):
            options = [options]
        return [str(opt).strip() for opt in options if str(opt).strip()]

    @property
    def clean_options(self) -> list:
        """Options telles qu'elles doivent être présentées à l'agent."""
        return self.normalize_options(self.options)

    def matches(self, response) -> bool:
        """
        True si `response` est la bonne réponse du QCM.

        La comparaison ignore la casse et les espaces de bord : un agent qui
        renvoie l'option exacte reçue ne doit pas être pénalisé par une
        différence de frappe invisible.
        """
        expected = (self.correct_answer or '').strip().casefold()
        given    = (response or '').strip().casefold()
        return bool(expected) and expected == given

    def clean(self):
        """
        Contrôles métier du QCM — seul format accepté.

        Appelé par `full_clean()` (admin Django) et par le serializer, qui
        normalise les options avant de valider.
        """
        super().clean()
        errors = {}

        if self.question_kind != self.QuestionKind.MCQ:
            errors['question_kind'] = (
                "Seul le format QCM est accepté pour une question d'évaluation."
            )

        options = self.clean_options
        if len(options) < self.MIN_OPTIONS:
            errors['options'] = (
                f'Un QCM doit proposer au moins {self.MIN_OPTIONS} options.'
            )
        elif len(options) > self.MAX_OPTIONS:
            errors['options'] = (
                f'Un QCM ne peut pas dépasser {self.MAX_OPTIONS} options.'
            )
        elif len({opt.casefold() for opt in options}) != len(options):
            errors['options'] = 'Deux options du QCM sont identiques.'

        expected = (self.correct_answer or '').strip()
        if not expected:
            errors['correct_answer'] = 'La bonne réponse est obligatoire.'
        elif options and expected.casefold() not in {o.casefold() for o in options}:
            errors['correct_answer'] = (
                "La bonne réponse doit être exactement l'une des options "
                "proposées."
            )

        if errors:
            raise ValidationError(errors)

    def __str__(self) -> str:
        return f"[{self.question_type}] Diff.{self.difficulty} — {self.text[:60]}"


class Exam(models.Model):
    """Examen (groupe de questions) créé par un évaluateur ou instructeur."""

    class ExamStatus(models.TextChoices):
        DRAFT     = 'DRAFT',     _('Brouillon')
        PUBLISHED = 'PUBLISHED', _('Publié')
        CLOSED    = 'CLOSED',    _('Fermé')

    training        = models.ForeignKey(Training, on_delete=models.SET_NULL, null=True,
                                        related_name='exams')
    title           = models.CharField(max_length=200)
    created_by      = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='exams_created',
    )
    questions       = models.ManyToManyField(Question, related_name='exams', blank=True)
    duration_minutes = models.PositiveIntegerField(default=60)
    passing_score   = models.PositiveSmallIntegerField(default=70)
    exam_status     = models.CharField(max_length=20, choices=ExamStatus.choices,
                                       default=ExamStatus.DRAFT)
    start_datetime  = models.DateTimeField(null=True, blank=True)
    end_datetime    = models.DateTimeField(null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'evaluations_exam'

    def __str__(self) -> str:
        return f"{self.title} [{self.exam_status}]"


class ExamSession(models.Model):
    """Session individuelle d'un agent sur un examen."""

    class SessionStatus(models.TextChoices):
        IN_PROGRESS      = 'IN_PROGRESS',      _('En cours')
        SUBMITTED        = 'SUBMITTED',         _('Soumise — en attente de correction')
        CORRECTING       = 'CORRECTING',        _('En cours de correction')
        PENDING_APPROVAL = 'PENDING_APPROVAL',  _('Correction à valider par le chef')
        GRADED           = 'GRADED',            _('Corrigée et validée')
        REJECTED         = 'REJECTED',          _('Correction rejetée par le chef')

    exam            = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='sessions')
    agent           = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='exam_sessions',
    )
    session_status  = models.CharField(max_length=20, choices=SessionStatus.choices,
                                       default=SessionStatus.IN_PROGRESS)
    score           = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                          verbose_name=_('Score /100 (officiel après approbation chef)'))
    is_passed       = models.BooleanField(null=True, blank=True)
    started_at      = models.DateTimeField(auto_now_add=True)
    submitted_at    = models.DateTimeField(null=True, blank=True)
    graded_at       = models.DateTimeField(null=True, blank=True)
    graded_by       = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sessions_graded',
        verbose_name=_('Évalué par'),
    )
    approved_by     = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sessions_approved',
        verbose_name=_('Validé par (chef d\'unité)'),
    )
    approved_at     = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, verbose_name=_('Motif de rejet du chef'))
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'evaluations_exam_session'
        constraints = [
            models.UniqueConstraint(
                fields=['exam', 'agent'],
                condition=models.Q(session_status='IN_PROGRESS'),
                name='unique_active_session_per_exam_agent',
            )
        ]

    def compute_score_from_items(self):
        """
        Calcule le score /100 a partir des scores attribues par l'evaluateur.

        Le bareme est celui de l'examen, et non celui des seules questions
        auxquelles l'agent a repondu : sinon un agent qui ne traite qu'une
        question sur dix et la reussit obtiendrait 100/100.
        Les questions laissees sans reponse comptent donc pour 0.

        Ne sauvegarde pas — le score n'est officiel qu'apres approbation du chef.
        Retourne un Decimal arrondi a 2 decimales.
        """
        answers = self.answers.select_related('question').all()

        # Bareme de reference = les questions actives de l'examen, auxquelles
        # s'ajoutent celles auxquelles l'agent a repondu.
        # Une question retiree de la banque (is_active=False) n'est plus
        # presentee aux candidats : la compter dans le bareme ferait baisser
        # le score de tout le monde. Mais si l'agent y a repondu avant son
        # retrait, elle doit rester au bareme, sinon les points obtenus se
        # rapporteraient a un total trop petit et le score pourrait depasser
        # 100.
        total_points = None
        if self.exam_id:
            total_points = self.exam.questions.filter(
                models.Q(is_active=True)
                | models.Q(id__in=[a.question_id for a in answers])
            ).distinct().aggregate(total=models.Sum('points'))['total']

        if not total_points:
            # Examen sans questions rattachees : on retombe sur les points
            # effectivement presentes a l'agent
            total_points = sum(a.question.points for a in answers)

        if not total_points:
            return Decimal('0.00')

        earned = sum((a.evaluator_score or Decimal('0')) for a in answers)
        score = (Decimal(earned) / Decimal(total_points)) * Decimal('100')
        return round(score, 2)

    def submit_for_approval(self, evaluator, score: float):
        """
        L'évaluateur soumet la correction corrigée pour validation du chef d'unité.
        Met à jour le statut et le score proposé, mais ne le rend pas officiel.
        """
        self.session_status  = self.SessionStatus.PENDING_APPROVAL
        self.score           = score    # provisoire — sera confirmé par le chef
        self.graded_by       = evaluator
        self.graded_at       = timezone.now()
        self.save(update_fields=['session_status', 'score', 'graded_by', 'graded_at', 'updated_at'])

    def approve(self, unit_chief):
        """
        Le chef d'unité approuve la correction.
        Le score devient officiel, is_passed est calculé.
        """
        self.session_status = self.SessionStatus.GRADED
        self.is_passed      = self.score is not None and self.score >= self.exam.passing_score
        self.approved_by    = unit_chief
        self.approved_at    = timezone.now()
        self.save(update_fields=[
            'session_status', 'is_passed', 'approved_by', 'approved_at', 'updated_at'
        ])

    def reject(self, unit_chief, reason: str):
        """
        Le chef d'unité rejette la correction — l'évaluateur doit recorriger.
        """
        self.session_status  = self.SessionStatus.REJECTED
        self.rejection_reason = reason
        self.approved_by     = unit_chief
        # Le score propose est invalide tant que la correction n'est pas reprise
        self.is_passed       = None
        self.save(update_fields=[
            'session_status', 'rejection_reason', 'approved_by', 'is_passed', 'updated_at',
        ])

    def __str__(self) -> str:
        return f"Session de {self.agent} sur '{self.exam}' [{self.session_status}]"


class Answer(models.Model):
    """
    Réponse d'un agent à une question lors d'une session.
    La correction est faite manuellement par l'évaluateur (evaluator_score).
    """

    session         = models.ForeignKey(ExamSession, on_delete=models.CASCADE, related_name='answers')
    question        = models.ForeignKey(Question, on_delete=models.CASCADE)
    response        = models.TextField(verbose_name=_('Réponse donnée par l\'agent'))

    # ─ Correction manuelle par l'évaluateur ────────────────────────────────────
    evaluator_score  = models.DecimalField(
        max_digits=4, decimal_places=2,
        null=True, blank=True,
        verbose_name=_('Score attribué par l\'eval (/points)'),
        help_text=_('Entre 0 et la valeur de points de la question.'),
    )
    is_correct       = models.BooleanField(
        null=True, blank=True,
        verbose_name=_('Réponse correcte ?'),
        help_text=_('Rempli par l\'evaluateur. NULL = pas encore corrigé.'),
    )
    feedback         = models.TextField(blank=True, verbose_name=_('Feedback de l\'evaluateur'))
    corrected_by     = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='answers_corrected',
        verbose_name=_('Corrigé par'),
    )
    corrected_at     = models.DateTimeField(null=True, blank=True)
    answered_at      = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'evaluations_answer'
        constraints = [
            models.UniqueConstraint(fields=['session', 'question'],
                                    name='unique_answer_per_session_question')
        ]

    @property
    def is_pending_correction(self) -> bool:
        """True si cette réponse n'a pas encore été corrigée par un évaluateur."""
        return self.evaluator_score is None and self.is_correct is None

    def apply_correction(self, evaluator, score: float, is_correct: bool, feedback: str = ''):
        """
        L'évaluateur corrige cette réponse.
        :param evaluator: User avec rôle EVALUATOR
        :param score: Score attribué (0 à question.points)
        :param is_correct: bool
        :param feedback: Commentaire de l'évaluateur
        """
        self.evaluator_score = score
        self.is_correct      = is_correct
        self.feedback        = feedback
        self.corrected_by    = evaluator
        self.corrected_at    = timezone.now()
        self.save(update_fields=[
            'evaluator_score', 'is_correct', 'feedback',
            'corrected_by', 'corrected_at', 'updated_at'
        ])

    def __str__(self) -> str:
        correct = '✓' if self.is_correct else ('✗' if self.is_correct is False else '?')
        return f"Réponse [{correct}] de {self.session.agent} à Q{self.question_id}"
