"""
Système de permissions basé sur les rôles fonctionnels.

Architecture : factory pattern pour éviter le boilerplate répétitif.
Chaque permission vérifie que l'utilisateur possède le rôle requis
via la table UserRole (et non via les groups Django natifs).
"""

from rest_framework.permissions import BasePermission


# =============================================================================
# Factory — génère une classe de permission à partir d'un rôle fonctionnel
# =============================================================================

def make_role_permission(role: str, allow_admin: bool = True):
    """
    Génère dynamiquement une classe de permission DRF pour un rôle donné.

    Usage :
        IsEvaluator  = make_role_permission('EVALUATOR')
        IsInstructor = make_role_permission('INSTRUCTOR')

    :param role: Valeur du champ UserRole.role (ex: 'EVALUATOR')
    :param allow_admin: Si True, les admins passent toujours (par défaut)
    """

    class RolePermission(BasePermission):
        required_role = role
        _allow_admin = allow_admin

        def has_permission(self, request, view):
            if not request.user or not request.user.is_authenticated:
                return False
            if self._allow_admin and request.user.is_admin:
                return True
            return request.user.has_role(self.required_role)

        def has_object_permission(self, request, view, obj):
            return self.has_permission(request, view)

    # 'UNIT_CHIEF'.capitalize() donnait 'Unit_chief' : on construit un nom propre
    pretty = ''.join(part.capitalize() for part in role.split('_'))
    RolePermission.__name__ = f'Is{pretty}'
    RolePermission.__qualname__ = f'Is{pretty}'
    return RolePermission


def make_any_role_permission(*roles: str, allow_admin: bool = True):
    """
    Genere une permission DRF qui passe si l'utilisateur possede AU MOINS UN
    des roles donnes. Evite d'empiler les classes composees a la main.

    Usage :
        IsEvaluatorOrUnitChief = make_any_role_permission('EVALUATOR', 'UNIT_CHIEF')
    """

    class AnyRolePermission(BasePermission):
        required_roles = roles
        _allow_admin = allow_admin

        def has_permission(self, request, view):
            if not request.user or not request.user.is_authenticated:
                return False
            if self._allow_admin and request.user.is_admin:
                return True
            return any(request.user.has_role(r) for r in self.required_roles)

        def has_object_permission(self, request, view, obj):
            return self.has_permission(request, view)

    pretty = 'Or'.join(
        ''.join(part.capitalize() for part in r.split('_')) for r in roles
    )
    AnyRolePermission.__name__ = f'Is{pretty}'
    AnyRolePermission.__qualname__ = f'Is{pretty}'
    return AnyRolePermission


# =============================================================================
# Permissions atomiques par rôle
# =============================================================================

IsAdministrator   = make_role_permission('ADMIN',       allow_admin=True)
IsEvaluator       = make_role_permission('EVALUATOR')
IsInstructor      = make_role_permission('INSTRUCTOR')
IsMentor          = make_role_permission('MENTOR')
IsApprover        = make_role_permission('APPROVER')
IsUnitChief       = make_role_permission('UNIT_CHIEF')

# Combinaisons utilisees par les vues de suivi (alertes J-14, retards, etc.)
IsEvaluatorOrUnitChief = make_any_role_permission('EVALUATOR', 'UNIT_CHIEF')
IsEvaluatorOrUnitChiefOrApprover = make_any_role_permission(
    'EVALUATOR', 'UNIT_CHIEF', 'APPROVER'
)


# =============================================================================
# Permissions composées (OR / AND logique)
# =============================================================================

class IsApproverOrUnitChief(BasePermission):
    """Approbateur OU chef d'unité — pour les validations de workflow."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_admin:
            return True
        return request.user.has_role('APPROVER') or request.user.has_role('UNIT_CHIEF')


class IsAdminOrOwner(BasePermission):
    """
    Administrateur OU propriétaire de la ressource.
    Le modèle doit exposer un champ/propriété `owner` ou `user`.
    """

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_admin:
            return True
        owner = getattr(obj, 'user', None) or getattr(obj, 'owner', None)
        return owner == request.user


class IsEvaluatorOrInstructor(BasePermission):
    """Évaluateur OU instructeur — pour la création d'évaluations."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_admin:
            return True
        return request.user.has_role('EVALUATOR') or request.user.has_role('INSTRUCTOR')


class IsReadOnly(BasePermission):
    """Accès en lecture seule — GET, HEAD, OPTIONS uniquement."""

    SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')

    def has_permission(self, request, view):
        return request.method in self.SAFE_METHODS
