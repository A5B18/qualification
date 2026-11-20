"""
Middleware d'audit — enregistre les requêtes POST/PUT/PATCH/DELETE des utilisateurs authentifiés.
Inséré dans MIDDLEWARE après AuthenticationMiddleware (voir settings/base.py).
"""

import json
import logging

from django.http.request import RawPostDataException

from .models import AuditLog

logger = logging.getLogger(__name__)


class AuditMiddleware:
    """
    Enregistre en base chaque action mutante d'un utilisateur authentifié.
    Méthodes surveillées : POST, PUT, PATCH, DELETE.
    Exclut les endpoints non critiques (swagger, static, media).
    """

    WRITE_METHODS   = frozenset({'POST', 'PUT', 'PATCH', 'DELETE'})
    EXCLUDED_PATHS  = ('/api/schema/', '/api/docs/', '/static/', '/media/', '/admin/')

    #: Champs retires du corps avant enregistrement.
    #
    # Seuls les mots de passe etaient masques. Le corps de
    # `POST /auth/logout/` contient un refresh token, celui de
    # `/auth/token/refresh/` aussi : la table d'audit conservait donc des
    # jetons utilisables, lisibles par tout administrateur et exportables.
    # Un journal d'audit ne doit jamais contenir de quoi se reconnecter.
    SENSITIVE_FIELDS = frozenset({
        'password', 'old_password', 'new_password', 'temp_password',
        'refresh', 'access', 'token',
    })
    REDACTED = '[masqué]'

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Enregistrer seulement si :
        # 1. Méthode mutante
        # 2. Utilisateur authentifié
        # 3. Chemin non exclu
        if (
            request.method in self.WRITE_METHODS
            and hasattr(request, 'user')
            and request.user.is_authenticated
            and not any(request.path.startswith(p) for p in self.EXCLUDED_PATHS)
        ):
            self._log_action(request, response)

        return response

    def _log_action(self, request, response):
        """Crée un AuditLog en base. Silencieux en cas d'erreur."""
        try:
            request_data = self._safe_body(request)

            AuditLog.objects.create(
                user=request.user,
                action=request.method,
                endpoint=request.path[:300],
                status_code=response.status_code,
                ip_address=self._get_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                request_data=request_data,
            )
        except Exception:
            # Ne jamais bloquer une requête pour un log raté
            logger.warning("AuditMiddleware: impossible de créer le log.", exc_info=True)

    @classmethod
    def _safe_body(cls, request):
        """
        Corps JSON de la requête, secrets masqués.

        Renvoie None si le corps n'est pas du JSON exploitable : un corps
        illisible ne doit pas empêcher l'enregistrement de l'action elle-même.
        """
        if 'application/json' not in (request.content_type or ''):
            return None
        try:
            body = json.loads(request.body)
        except (ValueError, UnicodeDecodeError, RawPostDataException):
            return None
        if not isinstance(body, dict):
            return body
        return {
            key: (cls.REDACTED if key.lower() in cls.SENSITIVE_FIELDS else value)
            for key, value in body.items()
        }

    @staticmethod
    def _get_ip(request) -> str:
        """Extrait l'IP réelle (prend en compte les proxies via X-Forwarded-For)."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')
