"""
Modèles de gestion des unités organisationnelles ASECNA.

Règle métier : un agent est affecté à une seule unité pour toute sa carrière.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class Unit(models.Model):
    """
    Unité organisationnelle ASECNA (ex: TWR Dakar, APP Abidjan…).
    Un agent est lié à une unité via AgentProfile.unit (FK protégée).
    """

    class UnitType(models.TextChoices):
        TWR   = 'TWR',   _('Tour de contrôle (TWR)')
        APP   = 'APP',   _('Approche (APP)')
        ACC   = 'ACC',   _('Centre de contrôle régional (ACC)')
        FIC   = 'FIC',   _('Centre d\'information de vol (FIC)')
        MET   = 'MET',   _('Météorologie')
        COM   = 'COM',   _('Télécommunications')
        ADMIN = 'ADMIN', _('Administratif')
        OTHER = 'OTHER', _('Autre')

    code        = models.CharField(max_length=20, unique=True, verbose_name=_('Code'))
    name        = models.CharField(max_length=100, verbose_name=_('Nom'))
    unit_type   = models.CharField(
        max_length=10,
        choices=UnitType.choices,
        verbose_name=_('Type d\'unité'),
    )
    location    = models.CharField(max_length=100, blank=True, verbose_name=_('Localisation'))
    country     = models.CharField(max_length=100, blank=True, verbose_name=_('Pays'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    is_active   = models.BooleanField(default=True, verbose_name=_('Active'))
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table            = 'units_unit'
        verbose_name        = _('Unité')
        verbose_name_plural = _('Unités')
        ordering = ['code']
        indexes = [
            models.Index(fields=['code'],      name='idx_unit_code'),
            models.Index(fields=['unit_type'], name='idx_unit_type'),
        ]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"
