"""
Settings de production — étend base.py.
Activer avec : DJANGO_SETTINGS_MODULE=config.settings.production
"""

from .base import *  # noqa

DEBUG = False

# En production, restreindre les origines CORS au domaine frontend
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='').split(',')  # noqa

# Sécurité HTTPS
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Logs en production : fichier rotatif.
# Le dossier doit exister AVANT que logging ne configure le handler, sinon
# dictConfig leve "ValueError: Unable to configure handler 'file'" et Django
# refuse de demarrer (c'etait le cas : le dossier logs/ n'etait pas cree).
LOG_DIR = BASE_DIR / 'logs'  # noqa
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

# SMTP en production
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')  # noqa
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)  # noqa
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')  # noqa
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')  # noqa
