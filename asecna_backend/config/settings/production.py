"""
Settings de production — étendent base.py.
Activer avec : DJANGO_SETTINGS_MODULE=config.settings.production
"""

from decouple import config

from .base import *  # noqa: F401,F403

DEBUG = False

# =============================================================================
# Secrets
#
# `base.py` fournit une clé de repli pour que `manage.py` démarre sans .env en
# développement. En production cette clé ne doit jamais servir : elle est
# publique (elle est dans le dépôt), et toute signature de session ou de jeton
# faite avec elle est forgeable. On exige donc une valeur explicite, et le
# démarrage échoue bruyamment si elle manque — plutôt que de servir en silence
# avec une clé connue de tous.
# =============================================================================
SECRET_KEY = config('SECRET_KEY')

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='').split(',')

# En production, restreindre les origines CORS au domaine frontend
CORS_ALLOWED_ORIGINS = [
    origin.strip() for origin in config('CORS_ALLOWED_ORIGINS', default='').split(',')
    if origin.strip()
]

# Django 4+ vérifie l'origine des requêtes POST non sûres (admin, formulaires) :
# sans cette liste, l'administration derrière un domaine HTTPS renvoie 403.
CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in config('CSRF_TRUSTED_ORIGINS', default='').split(',')
    if origin.strip()
] or CORS_ALLOWED_ORIGINS

# =============================================================================
# Sécurité HTTPS
# =============================================================================
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Derrière un reverse proxy (nginx, load balancer), Django ne voit que du HTTP :
# sans cet en-tête, `SECURE_SSL_REDIRECT` boucle indéfiniment et
# `request.is_secure()` reste faux.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Durcissements complémentaires : le cookie de session n'a pas à être lisible
# en JavaScript, ni envoyé lors d'une navigation entrante depuis un autre site.
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'

# =============================================================================
# Journalisation : fichier rotatif.
#
# Le dossier doit exister AVANT que logging ne configure le handler, sinon
# dictConfig leve "ValueError: Unable to configure handler 'file'" et Django
# refuse de demarrer.
# =============================================================================
LOG_DIR = BASE_DIR / 'logs'  # noqa: F405
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} — {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'asecna.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {'handlers': ['file'], 'level': 'WARNING'},
        'apps': {'handlers': ['file'], 'level': 'INFO'},
    },
}

# =============================================================================
# Courriel (SMTP)
# =============================================================================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

# Expéditeur des messages applicatifs (réinitialisation de mot de passe).
# Sans ce réglage, Django utilisait « webmaster@localhost », que la plupart des
# relais SMTP rejettent.
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default=EMAIL_HOST_USER or 'no-reply@asecna.org')
SERVER_EMAIL = DEFAULT_FROM_EMAIL
