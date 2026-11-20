"""
Settings de test — étendent le développement.

Activer avec : DJANGO_SETTINGS_MODULE=config.settings.test

Pourquoi un module dédié (convention Django) plutôt que de réutiliser
`development` :

  - le hachage des mots de passe passe en MD5. PBKDF2 est conçu pour être
    lent ; chaque classe de test crée une dizaine de comptes, et le hachage
    représentait l'essentiel de la durée de la suite ;
  - la base de test vit en mémoire, sans écriture disque ;
  - la journalisation est réduite aux erreurs : la sortie des tests redevient
    lisible, et les avertissements attendus (403, 400 métier) ne la noient
    plus.

Aucun réglage fonctionnel n'est modifié : les tests exercent les mêmes
validateurs, les mêmes permissions et les mêmes règles métier.
"""

from .development import *  # noqa: F401,F403

# Hachage rapide — réservé aux tests, jamais à un environnement servi.
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# La barre de débogage n'a pas de sens hors navigateur et ajoute un middleware
# à chaque requête de test.
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != 'debug_toolbar']  # noqa: F405
MIDDLEWARE = [m for m in MIDDLEWARE  # noqa: F405
              if 'debug_toolbar' not in m]

# Les quotas de connexion sont desactives : la suite enchaine des dizaines
# d'authentifications depuis la meme adresse, et un test ne doit pas echouer
# parce qu'un autre a consomme le quota. Le quota lui-meme est verifie par un
# test dedie, qui reactive un taux explicite (`override_settings`).
REST_FRAMEWORK = {  # noqa: F405
    **REST_FRAMEWORK,  # noqa: F405
    'DEFAULT_THROTTLE_RATES': {'login': None, 'password_change': None},
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': 'ERROR'},
    'loggers': {
        # `django.request` journalise en WARNING chaque 4xx. Les tests en
        # provoquent volontairement (403 attendus, 400 metier) : sans cette
        # ligne, la sortie de la suite est noyee sous des avertissements qui
        # signalent en realite des assertions reussies.
        'django': {'handlers': ['console'], 'level': 'ERROR', 'propagate': False},
        'apps': {'handlers': ['console'], 'level': 'ERROR', 'propagate': False},
    },
}
