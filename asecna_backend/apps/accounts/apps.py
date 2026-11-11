from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'
    verbose_name = 'Comptes & Authentification'

    def ready(self):
        """Connecte les signaux au démarrage de l'app."""
        import apps.accounts.signals  # noqa: F401
