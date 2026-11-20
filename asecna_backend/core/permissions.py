"""
Système de permissions basé sur les rôles fonctionnels.

Architecture : une fabrique unique produit toutes les classes de permission à
partir de la liste des rôles autorisés. Chaque permission interroge la table
`UserRole` (et non les groupes Django natifs), via `User.has_any_role()` qui
mémorise les rôles actifs pour la durée de la requête.

Les classes composées étaient auparavant écrites à la main en dupliquant le
corps de la fabrique ; elles en dérivent désormais, ce qui garantit qu'elles
suivent les mêmes règles (admin toujours autorisé, anonyme toujours refusé).
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission


# =============================================================================
# Fabrique
# =============================================================================

def make_any_role_permission(*roles: str, allow_admin: bool = True):
    """
    Génère une classe de permission DRF qui passe si l'utilisateur possède
    AU MOINS UN des rôles donnés.

    Usage :
        IsEvaluator            = make_any_role_permission('EVALUATOR')
        IsEvaluatorOrUnitChief = make_any_role_permission('EVALUATOR', 'UNIT_CHIEF')

    :param roles: valeurs de `UserRole.role` (ex: 'EVALUATOR')
    :param allow_admin: si True, les administrateurs passent toujours
    """

    class AnyRolePermission(BasePermission):
        required_roles = roles
        _allow_admin = allow_admin

        def has_permission(self, request, view):
            user = request.user
            if not user or not user.is_authenticated:
                return False
            if self._allow_admin and user.is_admin:
                return True
            return user.has_any_role(*self.required_roles)

        def has_object_permission(self, request, view, obj):
            return self.has_permission(request, view)

    # 'UNIT_CHIEF'.capitalize() donnerait 'Unit_chief' : on construit un nom
    # propre, lisible dans les messages d'erreur et le schéma OpenAPI.
    pretty = 'Or'.join(
        ''.join(part.capitalize() for part in role.split('_')) for role in roles
    )
    AnyRolePermission.__name__ = f'Is{pretty}'
    AnyRolePermission.__qualname__ = f'Is{pretty}'
    return AnyRolePermission


def make_role_permission(role: str, allow_admin: bool = True):
    """Cas particulier à un seul rôle — conservé pour la lisibilité des vues."""
    return make_any_role_permission(role, allow_admin=allow_admin)


# =============================================================================
# Permissions par rôle
# =============================================================================

IsAdministrator = make_role_permission('ADMIN')
IsEvaluator     = make_role_permission('EVALUATOR')
IsInstructor    = make_role_permission('INSTRUCTOR')
IsMentor        = make_role_permission('MENTOR')
IsApprover      = make_role_permission('APPROVER')
IsUnitChief     = make_role_permission('UNIT_CHIEF')


# =============================================================================
# Combinaisons utilisées par les vues
# =============================================================================

#: Décideurs du workflow d'approbation.
IsApproverOrUnitChief = make_any_role_permission('APPROVER', 'UNIT_CHIEF')

#: Création et composition des évaluations.
IsEvaluatorOrInstructor = make_any_role_permission('EVALUATOR', 'INSTRUCTOR')

#: Écrans de suivi (alertes J-14, contrôles en retard).
IsEvaluatorOrUnitChief = make_any_role_permission('EVALUATOR', 'UNIT_CHIEF')
IsEvaluatorOrUnitChiefOrApprover = make_any_role_permission(
    'EVALUATOR', 'UNIT_CHIEF', 'APPROVER',
)

#: Consultation des dossiers d'un autre agent (annuaire, carnets, rapports).
IsSupervisor = make_any_role_permission('UNIT_CHIEF', 'APPROVER')


# =============================================================================
# Permissions non liées à un rôle
# =============================================================================

class IsAdminOrOwner(BasePermission):
    """
    Administrateur OU propriétaire de la ressource.
    Le modèle doit exposer un champ/propriété `user` ou `owner`.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_admin:
            return True
        owner = getattr(obj, 'user', None) or getattr(obj, 'owner', None)
        return owner == user


class IsReadOnly(BasePermission):
    """Accès en lecture seule — méthodes sûres uniquement (GET, HEAD, OPTIONS)."""

    def has_permission(self, request, view):
        # `SAFE_METHODS` vient de DRF : la liste était redéfinie ici, au risque
        # de diverger de la définition du framework.
        return request.method in SAFE_METHODS
