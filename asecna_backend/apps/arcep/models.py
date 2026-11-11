"""
App arcep — Carnet ARCEP (journal d'activités signé par le chef d'unité).

Structure :
  ARCEPBook  → Carnet d'un agent (un seul par agent)
  ARCEPEntry → Entrée d'activité quotidienne
  ARCEPSignature → Signature du chef d'unité (périodique)
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class ARCEPBook(models.Model):
    """Carnet ARCEP d'un agent — unique par agent."""

    agent       = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='arcep_book', verbose_name=_('Agent'),
    )
    opened_at   = models.DateField(auto_now_add=True)
    is_active   = models.BooleanField(default=True)

    class Meta:
        db_table = 'arcep_book'

    def __str__(self) -> str:
        return f"Carnet ARCEP de {self.agent}"


class ARCEPEntry(models.Model):
    """Entrée d'activité dans le carnet ARCEP.

    Règle métier : une entrée est valide uniquement si elle est couverte
    par une signature du chef d'unité (la période de signature englobe sa date).
    """

    book        = models.ForeignKey(ARCEPBook, on_delete=models.CASCADE, related_name='entries')
    entry_date  = models.DateField(verbose_name=_('Date'))
    activity    = models.TextField(verbose_name=_('Activité réalisée'))
    duration_hours = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    notes       = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'arcep_entry'
        ordering = ['-entry_date']

    @property
    def is_validated(self) -> bool:
        """
        True si cette entrée est couverte par au moins une signature du chef d'unité.
        Règle métier : une entrée non signée n'est pas officielle.
        """
        return self.book.signatures.filter(
            period_start__lte=self.entry_date,
            period_end__gte=self.entry_date,
        ).exists()

    def __str__(self) -> str:
        validated = " ✅" if self.is_validated else " ⏳"
        return f"Entrée {self.entry_date}{validated} — {self.book.agent}"


class ARCEPSignature(models.Model):
    """Signature périodique du chef d'unité sur le carnet ARCEP.

    Règle métier : seul un UNIT_CHIEF peut signer. La signature valide
    toutes les entrées comprises dans la période [period_start, period_end].
    """

    book        = models.ForeignKey(ARCEPBook, on_delete=models.CASCADE, related_name='signatures')
    unit_chief  = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='arcep_signatures',
    )
    period_start = models.DateField(verbose_name=_('Début période signée'))
    period_end   = models.DateField(verbose_name=_('Fin période signée'))
    comment      = models.TextField(blank=True, verbose_name=_('Commentaire'))
    signed_at    = models.DateTimeField(auto_now_add=True, verbose_name=_('Signé le'))
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'arcep_signature'
        verbose_name = _('Signature ARCEP')
        verbose_name_plural = _('Signatures ARCEP')
        constraints = [
            # Eviter les signatures en doublon sur la même période pour le même carnet
            models.UniqueConstraint(
                fields=['book', 'period_start', 'period_end'],
                name='unique_arcep_signature_period',
            )
        ]

    @property
    def entries_count(self) -> int:
        """Nombre d'entrées couvertes par cette signature."""
        return self.book.entries.filter(
            entry_date__gte=self.period_start,
            entry_date__lte=self.period_end,
        ).count()

    def __str__(self) -> str:
        return f"Signature {self.period_start}→{self.period_end} — {self.book.agent} (chef: {self.unit_chief})"
