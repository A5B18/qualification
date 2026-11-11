"""
Modèles d'authentification et de gestion des utilisateurs ASECNA.

Architecture en 3 entités indépendantes :
  1. User          → qui tu es (identité, auth)
  2. UserRole      → ce que tu fais (rôle fonctionnel, tracé)
  3. AgentProfile  → où tu en es dans ton parcours (statut)
"""

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from typing import Optional, List

from core.validators import validate_matricule, validate_phone
from .managers import UserManager


# =============================================================================
# Choix des rôles fonctionnels
# =============================================================================

class FunctionalRole(models.TextChoices):
    """
    Rôles fonctionnels — ce que l'agent FAIT dans le système.
    Indépendant du statut de parcours.
    """
    AGENT      = 'AGENT',      _('Agent')
    EVALUATOR  = 'EVALUATOR',  _('Évaluateur')
    INSTRUCTOR = 'INSTRUCTOR', _('Instructeur')
    MENTOR     = 'MENTOR',     _('Mentor')
    APPROVER   = 'APPROVER',   _('Approbateur')
    UNIT_CHIEF = 'UNIT_CHIEF', _('Chef d\'unité')
    ADMIN      = 'ADMIN',      _('Administrateur')


# =============================================================================
# Choix des statuts de parcours agent
# =============================================================================

class AgentStatus(models.TextChoices):
    """
    Statut de parcours — ce que l'agent EST dans son cycle de vie ASECNA.
    Un seul statut actif à la fois (évolution linéaire sauf suspension).
    """
    NEW        = 'NEW',        _('Nouveau')
    PROBATION  = 'PROBATION',  _('En période d\'essai')
    MENTORED   = 'MENTORED',   _('En mentorat')
    TRAINEE    = 'TRAINEE',    _('En formation')
    QUALIFIED  = 'QUALIFIED',  _('Qualifié')
    SUSPENDED  = 'SUSPENDED',  _('Suspendu')
    RETIRED    = 'RETIRED',    _('Retraité')


# =============================================================================
# Modèle User custom (AbstractBaseUser)
# =============================================================================

class User(AbstractBaseUser, PermissionsMixin):
    """
    Modèle utilisateur central ASECNA.

    Identifiant : matricule (format ASE-YYYY-NNNN) au lieu du username natif.
    Séparation stricte : ce modèle gère l'identité et l'authentification uniquement.
    Le rôle fonctionnel et le statut de parcours sont dans des modèles dédiés.
    """

    # -------------------------------------------------------------------------
    # Identité
    # -------------------------------------------------------------------------
    matricule   = models.CharField(
        max_length=20,
        unique=True,
        validators=[validate_matricule],
        verbose_name=_('Matricule'),
        help_text=_('Format : ASE-YYYY-NNNN, ex: ASE-2024-0001'),
    )
    email       = models.EmailField(unique=True, verbose_name=_('Email'))
    first_name  = models.CharField(max_length=100, verbose_name=_('Prénom'))
    last_name   = models.CharField(max_length=100, verbose_name=_('Nom'))
    phone       = models.CharField(
        max_length=20,
        blank=True,
        validators=[validate_phone],
        verbose_name=_('Téléphone'),
    )
    photo       = models.ImageField(
        upload_to='users/photos/',
        null=True,
        blank=True,
        verbose_name=_('Photo'),
    )

    # -------------------------------------------------------------------------
    # Flags Django obligatoires
    # -------------------------------------------------------------------------
    is_active   = models.BooleanField(default=True,  verbose_name=_('Actif'))
    is_staff    = models.BooleanField(default=False, verbose_name=_('Staff Django'))

    # -------------------------------------------------------------------------
    # Méta-données
    # -------------------------------------------------------------------------
    date_joined = models.DateTimeField(default=timezone.now, verbose_name=_('Date de création'))
    last_login  = models.DateTimeField(null=True, blank=True, verbose_name=_('Dernière connexion'))

    # -------------------------------------------------------------------------
    # Manager et configuration AbstractBaseUser
    # -------------------------------------------------------------------------
    objects = UserManager()

    USERNAME_FIELD  = 'matricule'
    REQUIRED_FIELDS = ['email', 'first_name', 'last_name']

    class Meta:
        db_table    = 'accounts_user'
        verbose_name        = _('Utilisateur')
        verbose_name_plural = _('Utilisateurs')
        ordering = ['matricule']
        indexes = [
            models.Index(fields=['email'],   name='idx_user_email'),
            models.Index(fields=['is_active'], name='idx_user_active'),
        ]

    # -------------------------------------------------------------------------
    # Propriétés utilitaires
    # -------------------------------------------------------------------------

    @property
    def full_name(self) -> str:
        """Nom complet formaté."""
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_admin(self) -> bool:
        """True si l'utilisateur a le rôle ADMIN ou est superuser Django."""
        return self.is_superuser or self.has_role(FunctionalRole.ADMIN)

    def get_full_name(self) -> str:
        """
        Nom complet — methode attendue par Django (admin, templates) et par
        une partie de l'ecosysteme. AbstractBaseUser ne la fournit pas, d'ou
        les AttributeError lorsqu'un appelant la supposait presente.
        """
        return self.full_name

    def get_short_name(self) -> str:
        """Nom court — pendant de get_full_name() dans le contrat Django."""
        return self.first_name or self.matricule

    def has_role(self, role: str) -> bool:
        """
        Vérifie si l'utilisateur possède un rôle fonctionnel actif.
        :param role: Valeur de FunctionalRole (ex: 'EVALUATOR')
        """
        return self.user_roles.filter(role=role, is_active=True).exists()

    def get_active_roles(self) -> List[str]:
        """Retourne la liste des rôles fonctionnels actifs de l'utilisateur."""
        return list(self.user_roles.filter(is_active=True).values_list('role', flat=True))

    def get_career_status(self) -> Optional[str]:
        """Retourne le statut de parcours depuis AgentProfile (ou None si pas de profil)."""
        try:
            return self.agent_profile.status
        except AgentProfile.DoesNotExist:
            return None

    def __str__(self) -> str:
        return f"{self.matricule} — {self.full_name}"


# =============================================================================
# UserRole — Rôles fonctionnels tracés
# =============================================================================

class UserRole(models.Model):
    """
    Table de liaison entre User et ses rôles fonctionnels.

    Design :
    - Un utilisateur peut avoir plusieurs rôles simultanément (ex: EVALUATOR + MENTOR).
    - Chaque attribution est tracée (qui a attribué, quand).
    - Désactivation par is_active=False (pas de suppression physique pour l'audit).
    """

    user        = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='user_roles',
        verbose_name=_('Utilisateur'),
    )
    role        = models.CharField(
        max_length=20,
        choices=FunctionalRole.choices,
        verbose_name=_('Rôle fonctionnel'),
    )
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='roles_assigned',
        verbose_name=_('Attribué par'),
    )
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Attribué le'))
    revoked_at  = models.DateTimeField(null=True, blank=True, verbose_name=_('Révoqué le'))
    is_active   = models.BooleanField(default=True, verbose_name=_('Actif'))
    notes       = models.TextField(blank=True, verbose_name=_('Notes'))

    class Meta:
        db_table            = 'accounts_user_role'
        verbose_name        = _('Rôle utilisateur')
        verbose_name_plural = _('Rôles utilisateur')
        # Un utilisateur ne peut avoir qu'un seul exemplaire actif de chaque rôle
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'role'],
                condition=models.Q(is_active=True),
                name='unique_active_role_per_user',
            )
        ]
        indexes = [
            models.Index(fields=['user', 'role', 'is_active'], name='idx_userrole_lookup'),
        ]

    def __str__(self) -> str:
        status = 'actif' if self.is_active else 'révoqué'
        return f"{self.user.matricule} — {self.role} ({status})"


# =============================================================================
# AgentProfile — Statut de parcours professionnel
# =============================================================================

class AgentProfile(models.Model):
    """
    Profil de parcours professionnel d'un agent.

    Design :
    - Relation OneToOne avec User : un seul profil par agent.
    - status : position dans le cycle de vie ASECNA (distinct du rôle).
    - unit   : affectation unique et définitive (règle métier ASECNA).
    - La FK `unit` utilise une chaîne pour éviter l'import circulaire avec l'app units.
    """

    user            = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='agent_profile',
        verbose_name=_('Utilisateur'),
    )
    status          = models.CharField(
        max_length=20,
        choices=AgentStatus.choices,
        default=AgentStatus.NEW,
        verbose_name=_('Statut de parcours'),
    )
    # FK vers Unit — chaîne pour éviter l'import circulaire
    unit            = models.ForeignKey(
        'units.Unit',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='agents',
        verbose_name=_('Unité d\'affectation'),
        help_text=_('Affectation unique et définitive selon les règles ASECNA'),
    )
    hire_date       = models.DateField(null=True, blank=True, verbose_name=_('Date de recrutement'))
    qualification_date = models.DateField(
        null=True, blank=True, verbose_name=_('Date de qualification')
    )
    specialty       = models.ForeignKey(
        'training.Specialty',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agents',
        verbose_name=_('Spécialité'),
    )
    notes           = models.TextField(blank=True, verbose_name=_('Notes internes'))
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table            = 'accounts_agent_profile'
        verbose_name        = _('Profil agent')
        verbose_name_plural = _('Profils agents')
        indexes = [
            models.Index(fields=['status'], name='idx_profile_status'),
            models.Index(fields=['unit'],   name='idx_profile_unit'),
        ]

    def __str__(self) -> str:
        return f"Profil de {self.user.matricule} — {self.status}"
