"""
Signaux Django pour l'app accounts.

Signal principal :
  - Quand AgentProfile passe au statut QUALIFIED,
    créer automatiquement un ARCEPBook pour l'agent
    (règle métier : carnet ARCEP créé automatiquement à la qualification)
"""

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone


@receiver(pre_save, sender='accounts.AgentProfile')
def track_status_change(sender, instance, **kwargs):
    """
    Mémorise l'ancien statut avant la sauvegarde pour détecter
    les transitions et déclencher les effets de bord.
    """
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            instance._previous_status = old.status
        except sender.DoesNotExist:
            instance._previous_status = None
    else:
        instance._previous_status = None


@receiver(post_save, sender='accounts.AgentProfile')
def on_agent_qualified(sender, instance, created, **kwargs):
    """
    Règle métier : le carnet ARCEP est créé automatiquement
    quand le statut de l'agent passe à QUALIFIED.

    On n'importe ici (import local) pour éviter les imports circulaires
    entre apps accounts et arcep.
    """
    from apps.accounts.models import AgentStatus

    previous = getattr(instance, '_previous_status', None)
    current  = instance.status

    # Transition vers QUALIFIED — nouvelle ou première création
    if current == AgentStatus.QUALIFIED and previous != AgentStatus.QUALIFIED:
        from apps.arcep.models import ARCEPBook
        book, created_book = ARCEPBook.objects.get_or_create(agent=instance.user)
        if created_book:
            # Log de création pour traçabilité
            import logging
            logger = logging.getLogger('apps.accounts.signals')
            logger.info(
                "ARCEPBook créé automatiquement pour %s suite au passage au statut QUALIFIED",
                instance.user.matricule,
            )
