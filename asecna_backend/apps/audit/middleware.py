"""
Middleware d'audit — enregistre les requêtes POST/PUT/PATCH/DELETE des utilisateurs authentifiés.
Inséré dans MIDDLEWARE après AuthenticationMiddleware (voir settings/base.py).
"""

import json
import logging

logger = logging.getLogger(__name__)


class AuditMiddleware:
    """
    Enregistre en base chaque action mutante d'un utilisateur authentifié.
    Méthodes surveillées : POST, PUT, PATCH, DELETE.
    Exclut les endpoints non critiques (swagger, static, media).
    """

    WRITE_METHODS   = frozenset({'POST', 'PUT', 'PATCH', 'DELETE'})
    EXCLUDED_PATHS  = ('/api/schema/', '/api/docs/', '/static/', '/media/', '/admin/')

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
            from .models import AuditLog

            # Extraire le corps de la requête (limiter la taille)
            request_data = None
            if request.content_type and 'application/json' in request.content_type:
                try:
                    request_data = json.loads(request.body)
                    # Ne jamais logguer les mots de passe
                    if isinstance(request_data, dict):
                        request_data.pop('password', None)
                        request_data.pop('old_password', None)
                        request_data.pop('new_password', None)
                except (json.JSONDecodeError, Exception):
                    request_data = None

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

    @staticmethod
    def _get_ip(request) -> str:
        """Extrait l'IP réelle (prend en compte les proxies via X-Forwarded-For)."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')
