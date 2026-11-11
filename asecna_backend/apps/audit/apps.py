from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.audit'
    verbose_name = 'Audit & Logs'

    def ready(self):
        """Connecte les signaux d'historique de connexion au démarrage."""
        import apps.audit.signals  # noqa: F401
