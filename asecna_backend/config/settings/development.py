"""
Settings de développement — étend base.py.
Activer avec : DJANGO_SETTINGS_MODULE=config.settings.development
"""

from .base import *  # noqa
from decouple import config  # noqa

DEBUG = True

# En développement, on allow tous les origines CORS pour le frontend React local
CORS_ALLOW_ALL_ORIGINS = True

# =============================================================================
# Base de données
#
# Par défaut : SQLite (aucune configuration requise, idéal pour la démo).
#
# Pour développer sur PostgreSQL à la place, poser USE_POSTGRES=True dans .env
# et renseigner les variables DB_* : la configuration PostgreSQL de base.py est
# alors conservée. Cela évite d'avoir à modifier ce fichier, et permet au
# service `db` de docker-compose d'être réellement utilisé.
USE_POSTGRES = config('USE_POSTGRES', default=False, cast=bool)  # noqa

if not USE_POSTGRES:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
# =============================================================================

# Logs SQL des requêtes en développement
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
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'INFO'},
        'django.db.backends': {'handlers': ['console'], 'level': 'DEBUG', 'propagate': False},
        'apps': {'handlers': ['console'], 'level': 'DEBUG'},
    },
}

# Email en console en développement
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Debug toolbar (optionnel)
try:
    import debug_toolbar  # noqa
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
    INTERNAL_IPS = ['127.0.0.1']
except ImportError:
    pass
