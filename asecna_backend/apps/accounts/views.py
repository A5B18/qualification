"""
Vues (ViewSets + APIViews) pour l'app accounts.

Endpoints :
  POST   /api/v1/auth/login/                 → JWT login
  POST   /api/v1/auth/logout/                → Blacklist du refresh token
  POST   /api/v1/auth/token/refresh/         → Nouveau access token
  GET    /api/v1/auth/me/                    → Profil personnel
  PUT    /api/v1/auth/change-password/       → Changer son mot de passe
  GET    /api/v1/auth/users/                 → Liste des utilisateurs (admin)
  POST   /api/v1/auth/users/                 → Créer un utilisateur (admin)
  GET    /api/v1/auth/users/{id}/            → Détail utilisateur
  PUT    /api/v1/auth/users/{id}/assign-role/  → Attribuer un rôle (admin)
  DELETE /api/v1/auth/users/{id}/revoke-role/  → Révoquer un rôle (admin)
  POST   /api/v1/auth/users/{id}/reset-password/ → Reset mot de passe (admin)
"""

import logging
import secrets
import string

from django.conf import settings as django_settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit.models import LoginHistory
from core.mixins import SoftDeleteMixin
from core.permissions import IsAdministrator
from core.throttling import LoginRateThrottle, PasswordChangeRateThrottle
from .models import UserRole
from .serializers import (
    CustomTokenObtainPairSerializer,
    UserSerializer,
    UserCreateSerializer,
    ChangePasswordSerializer,
    AssignRoleSerializer,
    UserMeSerializer,
    LogoutSerializer,
)

User = get_user_model()

logger = logging.getLogger(__name__)


# =============================================================================
# Authentification JWT
# =============================================================================

class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Login : retourne access+refresh token avec claims enrichis (roles, status).

    Enregistre aussi la tentative dans LoginHistory. simplejwt n'emet pas les
    signaux `user_logged_in` / `user_login_failed` de Django : sans ce code,
    l'historique des connexions expose par /api/v1/audit/logins/ restait vide.
    """
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]
    # Sans quota, un matricule connu pouvait etre attaque par force brute :
    # l'historique tracait les echecs sans jamais les freiner.
    throttle_classes = [LoginRateThrottle]

    def post(self, request, *args, **kwargs):
        matricule = str(request.data.get('matricule', ''))[:20]
        try:
            response = super().post(request, *args, **kwargs)
        except Exception:
            self._record_login(request, matricule, success=False)
            raise
        self._record_login(
            request, matricule,
            success=200 <= response.status_code < 300,
        )
        return response

    @staticmethod
    def _record_login(request, matricule, success: bool):
        """Trace la tentative de connexion sans jamais faire echouer le login."""
        try:
            user = User.objects.filter(matricule=matricule).first() if success else None
            forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
            ip = (forwarded.split(',')[0].strip() if forwarded
                  else request.META.get('REMOTE_ADDR') or None)

            LoginHistory.objects.create(
                user=user,
                matricule_attempted=matricule,
                result=(LoginHistory.LoginResult.SUCCESS if success
                        else LoginHistory.LoginResult.FAILURE),
                ip_address=ip,
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            )
        except Exception:
            # Une trace d'audit manquante ne doit jamais empecher une
            # authentification valide : on journalise et on continue.
            logger.warning(
                "Impossible d'enregistrer la tentative de connexion.", exc_info=True,
            )


class LogoutView(generics.GenericAPIView):
    """
    Logout : blackliste le refresh token.
    Le client doit supprimer le access token localement.
    """
    # Requis par drf-spectacular pour introspecter la vue : sans serializer,
    # l'endpoint etait exclu du schema OpenAPI (absent de Swagger).
    serializer_class = LogoutSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': {'code': 'bad_request', 'message': 'Refresh token requis.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(serializer.validated_data['refresh'])
            token.blacklist()
        except TokenError:
            # `except Exception` masquait aussi les pannes de base : on ne
            # rattrape plus que le jeton invalide ou expire, ce que simplejwt
            # signale par TokenError.
            return Response(
                {'error': {'code': 'bad_request', 'message': 'Token invalide ou expiré.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({'message': 'Déconnexion réussie.'}, status=status.HTTP_200_OK)


class MeView(generics.RetrieveUpdateAPIView):
    """Profil personnel de l'utilisateur connecté."""
    serializer_class = UserMeSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(generics.GenericAPIView):
    """Changement de mot de passe par l'utilisateur lui-même."""
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]
    # Borne les essais sur `old_password` depuis un jeton derobe.
    throttle_classes = [PasswordChangeRateThrottle]

    def put(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'message': 'Mot de passe modifié avec succès.'})

    def post(self, request, *args, **kwargs):
        """Alias POST — la plupart des clients HTTP postent ce formulaire."""
        return self.put(request, *args, **kwargs)


# =============================================================================
# Gestion des utilisateurs (admin)
# =============================================================================

class UserViewSet(SoftDeleteMixin, viewsets.ModelViewSet):
    """
    CRUD des utilisateurs.

    Lecture (list / retrieve) : ouverte à tout utilisateur authentifié.
      L'annuaire des agents est consulté par les chefs d'unité, évaluateurs,
      mentors et instructeurs (page « Agents », listes déroulantes de
      sélection d'agent). Il était auparavant réservé aux administrateurs,
      ce qui renvoyait 403 et vidait ces écrans pour 5 rôles sur 7.
      Les agents sans rôle d'encadrement ne voient que leur propre fiche.

    Écriture (create / update / delete) et actions de gestion des rôles :
      administrateurs uniquement.
    """
    queryset = User.objects.all().order_by('matricule')

    # Rôles autorisés à consulter l'annuaire complet des agents
    DIRECTORY_ROLES = ('UNIT_CHIEF', 'APPROVER', 'EVALUATOR', 'MENTOR', 'INSTRUCTOR')

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdministrator()]

    def get_queryset(self):
        user = self.request.user
        # select_related/prefetch_related : le serializer lit le profil et les
        # rôles de chaque utilisateur (sinon 2 requêtes SQL par ligne listée)
        base = User.objects.select_related(
            'agent_profile', 'agent_profile__unit', 'agent_profile__specialty',
        ).prefetch_related('user_roles')

        # `has_any_role` : une seule requete pour les cinq roles, et les
        # controles suivants de la meme requete HTTP lisent le cache
        # d'instance (cf. `User._active_roles`).
        if user.is_admin or user.has_any_role(*self.DIRECTORY_ROLES):
            qs = base.all()
        else:
            # Agent simple : il ne consulte que sa propre fiche
            qs = base.filter(pk=user.pk)

        # Filtres optionnels de l'annuaire
        unit_id = self.request.query_params.get('unit')
        if unit_id:
            qs = qs.filter(agent_profile__unit_id=unit_id)
        agent_status = self.request.query_params.get('status')
        if agent_status:
            qs = qs.filter(agent_profile__status=agent_status)
        role = self.request.query_params.get('role')
        if role:
            qs = qs.filter(user_roles__role=role, user_roles__is_active=True)
        is_active = self.request.query_params.get('is_active')
        if is_active in ('true', 'True', '1'):
            qs = qs.filter(is_active=True)
        elif is_active in ('false', 'False', '0'):
            qs = qs.filter(is_active=False)
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(matricule__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
            )
        return qs.distinct().order_by('matricule')

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    @action(detail=True, methods=['post'], url_path='assign-role')
    def assign_role(self, request, pk=None):
        """Attribuer un rôle fonctionnel à un utilisateur."""
        user = self.get_object()
        serializer = AssignRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        role  = serializer.validated_data['role']
        notes = serializer.validated_data['notes']

        # Vérifier si le rôle est déjà actif
        if user.has_role(role):
            return Response(
                {'error': {'code': 'conflict', 'message': f"L'utilisateur a déjà le rôle {role}."}},
                status=status.HTTP_409_CONFLICT,
            )

        UserRole.objects.create(
            user=user,
            role=role,
            assigned_by=request.user,
            notes=notes,
        )
        # Les roles de cette instance sont memorises : sans invalidation, un
        # controle ulterieur dans la meme requete verrait l'etat d'avant.
        user.invalidate_role_cache()
        return Response(
            {'message': f"Rôle {role} attribué à {user.matricule}."},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['delete'], url_path='revoke-role')
    def revoke_role(self, request, pk=None):
        """Révoquer un rôle fonctionnel d'un utilisateur."""
        user = self.get_object()
        role = request.data.get('role')
        if not role:
            return Response(
                {'error': {'code': 'bad_request', 'message': 'Le champ role est requis.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        updated = UserRole.objects.filter(user=user, role=role, is_active=True).update(
            is_active=False,
            revoked_at=timezone.now(),
        )
        if not updated:
            return Response(
                {'error': {'code': 'not_found', 'message': f"Rôle {role} non trouvé ou déjà révoqué."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        user.invalidate_role_cache()
        return Response({'message': f"Rôle {role} révoqué pour {user.matricule}."})

    @action(detail=True, methods=['post'], url_path='reset-password')
    def reset_password(self, request, pk=None):
        """
        Reset du mot de passe par l'administrateur.

        Genere un mot de passe temporaire aleatoire de 12 caracteres, puis
        l'envoie a l'agent par courriel.

        Le mot de passe en clair n'est renvoye dans la reponse HTTP que si
        l'envoi n'a pas pu se faire (pas d'adresse connue, SMTP indisponible,
        ou backend `console` en developpement). Auparavant il etait renvoye
        systematiquement : il se retrouvait dans les journaux d'acces, dans le
        cache du navigateur et dans l'historique Swagger.
        """
        user = self.get_object()
        alphabet = string.ascii_letters + string.digits + '!@#$%'
        temp_password = ''.join(secrets.choice(alphabet) for _ in range(12))

        user.set_password(temp_password)
        user.save(update_fields=['password'])

        delivered = self._send_temp_password(user, temp_password)

        payload = {
            'message': f"Mot de passe réinitialisé pour {user.matricule}.",
            'delivered_by_email': delivered,
        }
        if not delivered:
            # Repli : sans courriel remis, l'administrateur doit pouvoir
            # transmettre le mot de passe de la main a la main.
            payload['temp_password'] = temp_password
            payload['message'] += (
                " L'envoi par courriel n'a pas abouti : communiquez-le "
                "directement à l'agent."
            )
        return Response(payload)

    @staticmethod
    def _send_temp_password(user, temp_password: str) -> bool:
        """
        Envoie le mot de passe temporaire. Retourne True si le courriel est
        parti. N'echoue jamais : un SMTP injoignable ne doit pas annuler la
        reinitialisation, deja ecrite en base.
        """
        if not user.email:
            return False
        try:
            # Les backends `console` et `dummy` n'acheminent rien : ils
            # impriment ou jettent le message. Les considerer comme remis
            # ferait perdre le mot de passe en developpement, ou personne ne
            # lit la sortie standard du serveur. L'administrateur garde donc
            # le repli dans ces deux cas seulement.
            backend = getattr(django_settings, 'EMAIL_BACKEND', '')
            if 'console' in backend or 'dummy' in backend:
                return False

            send_mail(
                subject="ASECNA — réinitialisation de votre mot de passe",
                message=(
                    f"Bonjour {user.full_name}," + '\n\n'
                    + "Votre mot de passe a été réinitialisé par un administrateur." + '\n'
                    + f"Mot de passe temporaire : {temp_password}" + '\n\n'
                    + f"Connectez-vous avec votre matricule {user.matricule} puis "
                    + "changez-le immédiatement depuis « Mon profil »." + '\n'
                ),
                from_email=getattr(django_settings, "DEFAULT_FROM_EMAIL", None),
                recipient_list=[user.email],
                fail_silently=False,
            )
            return True
        except Exception:
            # Un SMTP injoignable ne doit pas annuler la reinitialisation,
            # deja ecrite en base : on bascule sur le repli manuel.
            logger.warning(
                "Envoi du mot de passe temporaire impossible pour %s.",
                user.matricule, exc_info=True,
            )
            return False
