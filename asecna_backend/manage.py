#!/usr/bin/env python
"""Utilitaire de ligne de commande Django pour les tâches d'administration."""

import os
import sys


def main():
    """Lance les tâches d'administration."""
    # Par défaut, utiliser les settings de développement
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Impossible d'importer Django. Assurez-vous que Django est installé "
            "et que l'environnement virtuel est activé."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
