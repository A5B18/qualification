"""
Manager custom pour le modèle User ASECNA.
Identifiant : matricule (ex: ASE-2024-0001) au lieu du username Django natif.
"""

from django.contrib.auth.models import BaseUserManager


class UserManager(BaseUserManager):
    """
    Manager pour le modèle User custom.
    - create_user()      : agent standard
    - create_superuser() : administrateur Django (accès admin interface)
    """

    def create_user(self, matricule: str, email: str, password: str = None, **extra_fields):
        """Crée et sauvegarde un utilisateur ordinaire."""
        if not matricule:
            raise ValueError("Le matricule est obligatoire.")
        if not email:
            raise ValueError("L'email est obligatoire.")

        email = self.normalize_email(email)
        user = self.model(matricule=matricule, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, matricule: str, email: str, password: str = None, **extra_fields):
        """Crée et sauvegarde un super-utilisateur (accès interface admin Django)."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Le superuser doit avoir is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Le superuser doit avoir is_superuser=True.")

        return self.create_user(matricule, email, password, **extra_fields)

    def get_by_natural_key(self, matricule: str):
        """Permet la connexion par matricule."""
        return self.get(matricule=matricule)
