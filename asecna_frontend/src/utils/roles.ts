/**
 * Habilitations côté interface.
 *
 * Le même prédicat « cet utilisateur a-t-il l'un de ces rôles ? » était
 * réécrit dans treize fichiers, avec des variantes : certains testaient
 * `is_admin`, d'autres seulement `is_superuser` et le rôle `ADMIN`, d'autres
 * encore enveloppaient le résultat dans `Boolean()` et renvoyaient donc
 * `boolean` là où les voisins renvoyaient `boolean | undefined`. Une règle
 * d'habilitation qui change devait être retrouvée treize fois.
 *
 * Ces fonctions ne remplacent pas les contrôles du serveur : elles décident
 * seulement de ce que l'écran propose. Toute règle appliquée ici existe aussi
 * dans `core/permissions.py` et dans les vues.
 */

import type { FunctionalRole, User } from '../types'

/** Administrateur : superutilisateur Django ou porteur du rôle ADMIN. */
export function isAdmin(user: User | null | undefined): boolean {
    return Boolean(user?.is_superuser || user?.is_admin || user?.roles?.includes('ADMIN'))
}

/**
 * True si l'utilisateur possède au moins un des rôles demandés.
 * L'administrateur passe toujours, comme côté serveur
 * (`make_any_role_permission(..., allow_admin=True)`).
 */
export function hasAnyRole(
    user: User | null | undefined,
    ...roles: FunctionalRole[]
): boolean {
    if (isAdmin(user)) return true
    const held = user?.roles ?? []
    return roles.some(role => held.includes(role))
}

/** True si l'utilisateur possède ce rôle précis (ou est administrateur). */
export function hasRole(user: User | null | undefined, role: FunctionalRole): boolean {
    return hasAnyRole(user, role)
}

/**
 * Rôle principal de l'utilisateur, par ordre d'habilitation décroissant.
 *
 * Un agent peut cumuler plusieurs rôles (évaluateur ET mentor, par exemple) ;
 * le menu latéral et le tableau de bord doivent pourtant en choisir un seul.
 * Les deux écrans en avaient chacun leur copie : ajouter un rôle imposait de
 * modifier les deux, et rien ne signalait l'oubli.
 */
export type RoleKey =
    | 'admin' | 'unit_chief' | 'approver'
    | 'evaluator' | 'mentor' | 'instructor' | 'agent'

/** Ordre de priorité : le premier rôle détenu l'emporte. */
const ROLE_PRIORITY: ReadonlyArray<[FunctionalRole, RoleKey]> = [
    ['UNIT_CHIEF', 'unit_chief'],
    ['APPROVER', 'approver'],
    ['EVALUATOR', 'evaluator'],
    ['MENTOR', 'mentor'],
    ['INSTRUCTOR', 'instructor'],
]

export function detectRole(user: User | null | undefined): RoleKey {
    if (isAdmin(user)) return 'admin'
    const held = user?.roles ?? []
    for (const [role, key] of ROLE_PRIORITY) {
        if (held.includes(role)) return key
    }
    return 'agent'
}
