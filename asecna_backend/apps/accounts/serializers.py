"""
Serializers pour l'app accounts.

CustomTokenObtainPairSerializer : JWT enrichi avec roles + status de l'agent.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import AgentProfile, FunctionalRole

User = get_user_model()


# =============================================================================
# Mots de passe
# =============================================================================

def run_password_validators(password: str, user=None) -> str:
    """
    Applique AUTH_PASSWORD_VALIDATORS et traduit l'erreur pour DRF.

    Le projet configure quatre validateurs (longueur, similarite avec
    l'identite, mots de passe courants, mots de passe numeriques), mais aucun
    n'etait execute par l'API : seule une longueur minimale de 8 caracteres
    etait verifiee par le serializer. « 12345678 » etait donc accepte a la
    creation d'un compte comme au changement de mot de passe, alors que
    l'admin Django le refusait.
    """
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(list(exc.messages)) from exc
    return password


# =============================================================================
# JWT custom — claims enrichis
# =============================================================================

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Surcharge le serializer JWT pour embarquer dans le token :
    - matricule   (identifiant ASECNA)
    - roles       (liste des rôles fonctionnels actifs)
    - status      (statut de parcours depuis AgentProfile)

    Le frontend React peut lire les droits SANS appel API supplémentaire.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Claims métier
        token['matricule'] = user.matricule
        token['full_name'] = user.full_name
        token['roles'] = user.get_active_roles()
        # Un superutilisateur Django n'a aucune ligne UserRole : sans ces claims
        # le frontend ne pouvait pas le reconnaitre comme administrateur.
        token['is_admin'] = user.is_admin
        token['is_superuser'] = user.is_superuser

        # Statut de parcours (null si pas encore de profil)
        token['status'] = user.get_career_status()

        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        # Ajouter les infos utilisateur dans la réponse (pas seulement dans le token)
        data['user'] = {
            'id': self.user.pk,
            'matricule': self.user.matricule,
            'full_name': self.user.full_name,
            'email': self.user.email,
            'roles': self.user.get_active_roles(),
            'status': self.user.get_career_status(),
            'is_admin': self.user.is_admin,
            'is_superuser': self.user.is_superuser,
            'is_staff': self.user.is_staff,
        }
        return data


# =============================================================================
# Serializers utilisateur
# =============================================================================

class AgentProfileSerializer(serializers.ModelSerializer):
    """Parcours professionnel d'un agent, imbriqué dans la fiche utilisateur."""

    unit_detail      = serializers.SerializerMethodField()
    specialty_detail = serializers.SerializerMethodField()

    class Meta:
        model  = AgentProfile
        fields = [
            'id', 'user', 'status', 'unit', 'unit_detail',
            'specialty', 'specialty_detail', 'hire_date',
            'qualification_date', 'notes',
        ]
        read_only_fields = ['id', 'user']

    def get_unit_detail(self, obj) -> dict | None:
        if obj.unit_id and obj.unit:
            return {
                'id': obj.unit.id,
                'code': obj.unit.code,
                'name': obj.unit.name,
                'unit_type': obj.unit.unit_type,
                'location': obj.unit.location,
            }
        return None

    def get_specialty_detail(self, obj) -> dict | None:
        if obj.specialty_id and obj.specialty:
            return {
                'id': obj.specialty.id,
                'code': obj.specialty.code,
                'name': obj.specialty.name,
            }
        return None


class _UserProfileFieldsMixin:
    """
    Champs partagés par UserSerializer et UserMeSerializer.

    Le frontend attend à la fois :
      - des champs plats (`full_name`, `is_admin`, `status`, `unit`, `hire_date`)
      - le parcours imbriqué (`agent_profile`) sur la fiche détaillée
      - les alias `user` / `user_detail` / `unit_detail` sur la liste des agents

    Sans eux, la liste des agents affichait des lignes vides et un
    superutilisateur Django était traité comme un simple agent (il n'a aucune
    ligne UserRole en base, donc `roles` est vide).
    """

    def _profile(self, obj):
        try:
            return obj.agent_profile
        except AgentProfile.DoesNotExist:
            return None

    def get_roles(self, obj) -> list[str]:
        return obj.get_active_roles()

    def get_status(self, obj) -> str | None:
        return obj.get_career_status()

    def get_full_name(self, obj) -> str:
        return obj.full_name

    def get_is_admin(self, obj) -> bool:
        return obj.is_admin

    def get_agent_profile(self, obj) -> dict | None:
        profile = self._profile(obj)
        if profile is None:
            return None
        return AgentProfileSerializer(profile).data

    def get_unit(self, obj) -> int | None:
        profile = self._profile(obj)
        return profile.unit_id if profile else None

    def get_unit_detail(self, obj) -> dict | None:
        profile = self._profile(obj)
        if profile is None:
            return None
        return AgentProfileSerializer().get_unit_detail(profile)

    def get_specialty_detail(self, obj) -> dict | None:
        profile = self._profile(obj)
        if profile is None:
            return None
        return AgentProfileSerializer().get_specialty_detail(profile)

    def get_hire_date(self, obj) -> str | None:
        profile = self._profile(obj)
        return profile.hire_date if profile else None

    def get_qualification_date(self, obj) -> str | None:
        profile = self._profile(obj)
        return profile.qualification_date if profile else None

    def get_user(self, obj) -> int:
        """Alias : la liste des agents navigue vers /agents/<user>."""
        return obj.pk

    def get_user_detail(self, obj) -> dict:
        """Alias : la liste des agents lit l'identité dans `user_detail`."""
        return {
            'id': obj.pk,
            'matricule': obj.matricule,
            'first_name': obj.first_name,
            'last_name': obj.last_name,
            'full_name': obj.full_name,
            'email': obj.email,
        }


class UserSerializer(_UserProfileFieldsMixin, serializers.ModelSerializer):
    """Sérialisation complète d'un utilisateur (lecture + écriture admin)."""

    roles         = serializers.SerializerMethodField()
    status        = serializers.SerializerMethodField()
    full_name     = serializers.SerializerMethodField()
    is_admin      = serializers.SerializerMethodField()
    agent_profile = serializers.SerializerMethodField()
    unit          = serializers.SerializerMethodField()
    unit_detail   = serializers.SerializerMethodField()
    specialty_detail   = serializers.SerializerMethodField()
    hire_date     = serializers.SerializerMethodField()
    qualification_date = serializers.SerializerMethodField()
    user          = serializers.SerializerMethodField()
    user_detail   = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = [
            'id', 'matricule', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'photo', 'is_active', 'is_staff', 'is_superuser',
            'date_joined', 'roles', 'status', 'is_admin',
            'agent_profile', 'unit', 'unit_detail', 'specialty_detail',
            'hire_date', 'qualification_date', 'user', 'user_detail',
        ]
        read_only_fields = [
            'id', 'matricule', 'date_joined', 'roles', 'status', 'full_name',
            'is_admin', 'is_superuser', 'is_staff', 'agent_profile', 'unit',
            'unit_detail', 'specialty_detail', 'hire_date', 'qualification_date',
            'user', 'user_detail',
        ]


class UserCreateSerializer(serializers.ModelSerializer):
    """Création d'un utilisateur par l'administrateur."""

    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            'matricule', 'email', 'first_name', 'last_name',
            'phone', 'password',
        ]

    def validate(self, attrs):
        # Les validateurs comparent le mot de passe a l'identite de l'agent
        # (matricule, nom, courriel) : on leur passe donc l'instance en cours
        # de construction, pas seulement la chaine.
        candidate = User(**{k: v for k, v in attrs.items() if k != 'password'})
        run_password_validators(attrs['password'], user=candidate)
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class LogoutSerializer(serializers.Serializer):
    """
    Déconnexion : le refresh token à blacklister.

    Déclaré pour que `LogoutView` expose un serializer : sans lui,
    drf-spectacular échouait à introspecter la vue et l'excluait
    silencieusement du schéma OpenAPI (endpoint absent de Swagger).
    """

    refresh = serializers.CharField(
        write_only=True,
        help_text="Refresh token obtenu à la connexion.",
    )


class ChangePasswordSerializer(serializers.Serializer):
    """Changement de mot de passe (utilisateur lui-même)."""

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("L'ancien mot de passe est incorrect.")
        return value

    def validate_new_password(self, value):
        return run_password_validators(value, user=self.context['request'].user)

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        # `update_fields` : seul le mot de passe change ici. Un save complet
        # reecrivait toutes les colonnes et pouvait ecraser une modification
        # concurrente du profil.
        user.save(update_fields=['password'])
        return user


class AssignRoleSerializer(serializers.Serializer):
    """Attribution d'un rôle fonctionnel à un utilisateur (par l'admin)."""

    role  = serializers.ChoiceField(choices=FunctionalRole.choices)
    notes = serializers.CharField(required=False, allow_blank=True, default='')


class UserMeSerializer(_UserProfileFieldsMixin, serializers.ModelSerializer):
    """Profil personnel de l'utilisateur connecté (lecture + mise à jour)."""

    roles         = serializers.SerializerMethodField()
    status        = serializers.SerializerMethodField()
    full_name     = serializers.SerializerMethodField()
    is_admin      = serializers.SerializerMethodField()
    agent_profile = serializers.SerializerMethodField()
    unit          = serializers.SerializerMethodField()
    unit_detail   = serializers.SerializerMethodField()
    hire_date     = serializers.SerializerMethodField()
    qualification_date = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = [
            'id', 'matricule', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'photo', 'roles', 'status', 'is_admin',
            'is_staff', 'is_superuser', 'is_active',
            'agent_profile', 'unit', 'unit_detail',
            'hire_date', 'qualification_date',
        ]
        read_only_fields = [
            'id', 'matricule', 'roles', 'status', 'full_name', 'is_admin',
            'is_staff', 'is_superuser', 'is_active', 'agent_profile',
            'unit', 'unit_detail', 'hire_date', 'qualification_date',
        ]
