"""
App audit — Log des connexions et actions critiques.

AuditLog  → Chaque requête POST/PUT/PATCH/DELETE d'un utilisateur authentifié
LoginHistory → Historique des connexions (succès & échecs)
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class AuditLog(models.Model):
    """Trace d'une action sensible effectuée par un utilisateur."""

    user        = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='audit_logs',
    )
    action      = models.CharField(max_length=20, verbose_name=_('Méthode HTTP'))
    endpoint    = models.CharField(max_length=300, verbose_name=_('Endpoint'))
    status_code = models.PositiveSmallIntegerField(verbose_name=_('Code réponse'))
    ip_address  = models.GenericIPAddressField(null=True, blank=True)
    user_agent  = models.CharField(max_length=500, blank=True)
    request_data = models.JSONField(null=True, blank=True,
                                    verbose_name=_('Données de la requête'))
    timestamp   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table            = 'audit_log'
        verbose_name        = _('Log d\'audit')
        verbose_name_plural = _('Logs d\'audit')
        ordering = ['-timestamp']
        indexes  = [
            models.Index(fields=['user', 'timestamp'],  name='idx_audit_user'),
            models.Index(fields=['endpoint'],           name='idx_audit_endpoint'),
        ]

    def __str__(self) -> str:
        return f"[{self.action}] {self.endpoint} — {self.user} ({self.status_code})"


class LoginHistory(models.Model):
    """Historique des tentatives de connexion."""

    class LoginResult(models.TextChoices):
        SUCCESS = 'SUCCESS', _('Succès')
        FAILURE = 'FAILURE', _('Échec')

    user        = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='login_history',
    )
    matricule_attempted = models.CharField(max_length=20, blank=True,
                                           verbose_name=_('Matricule entré'))
    result      = models.CharField(max_length=10, choices=LoginResult.choices)
    ip_address  = models.GenericIPAddressField(null=True, blank=True)
    user_agent  = models.CharField(max_length=500, blank=True)
    timestamp   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_login_history'
        ordering = ['-timestamp']
        indexes  = [models.Index(fields=['user', 'timestamp'], name='idx_login_user')]

    def __str__(self) -> str:
        return f"Login {self.result} — {self.matricule_attempted} @ {self.timestamp}"
