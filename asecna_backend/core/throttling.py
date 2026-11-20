"""
Limitation de débit — protection des points d'entrée sensibles.

L'authentification n'était pas limitée : rien n'empêchait d'essayer des
milliers de mots de passe sur un matricule. `LoginHistory` enregistrait bien
chaque échec, mais aucun mécanisme ne les freinait — la trace documentait
l'attaque sans la gêner.

Les quotas sont définis dans `REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']`
(settings/base.py) et désactivés dans les settings de test.
"""

from rest_framework.throttling import AnonRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """
    Quota des tentatives de connexion, par adresse IP.

    `AnonRateThrottle` convient : une demande de jeton arrive toujours
    non authentifiée. Le compteur est tenu dans le cache Django ; avec le
    cache local par défaut, il est propre à chaque processus (voir la note de
    déploiement du README).
    """

    scope = 'login'


class PasswordChangeRateThrottle(AnonRateThrottle):
    """
    Quota des changements de mot de passe, pour borner les essais sur
    `old_password` par un porteur de jeton volé.
    """

    scope = 'password_change'

    def get_cache_key(self, request, view):
        # Ici l'appelant est authentifié : on compte par utilisateur plutôt
        # que par IP, sans quoi `AnonRateThrottle` ne compterait rien.
        if not request.user or not request.user.is_authenticated:
            return None
        return self.cache_format % {'scope': self.scope, 'ident': request.user.pk}
