"""
Signaux de l'app audit.

Le modele LoginHistory existait, etait expose par l'API et l'admin, mais
rien ne l'alimentait : l'historique des connexions restait vide. Ces
recepteurs enregistrent les connexions reussies et les echecs.
"""

import logging

from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def _client_ip(request):
    if request is None:
        return None
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR') or None


def _user_agent(request):
    if request is None:
        return ''
    return request.META.get('HTTP_USER_AGENT', '')[:500]


@receiver(user_logged_in)
def log_successful_login(sender, request, user, **kwargs):
    """Trace une connexion reussie (admin Django et API JWT)."""
    from .models import LoginHistory
    try:
        LoginHistory.objects.create(
            user=user,
            matricule_attempted=user.matricule,
            result=LoginHistory.LoginResult.SUCCESS,
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
        )
    except Exception:
        logger.warning("Impossible d'enregistrer la connexion reussie.", exc_info=True)


@receiver(user_login_failed)
def log_failed_login(sender, credentials, request=None, **kwargs):
    """Trace une tentative de connexion echouee."""
    from .models import LoginHistory
    try:
        matricule = (credentials or {}).get('matricule') or (credentials or {}).get('username') or ''
        LoginHistory.objects.create(
            user=None,
            matricule_attempted=str(matricule)[:20],
            result=LoginHistory.LoginResult.FAILURE,
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
        )
    except Exception:
        logger.warning("Impossible d'enregistrer l'echec de connexion.", exc_info=True)
