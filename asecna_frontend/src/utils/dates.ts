import { useState } from 'react'

const MS_PER_DAY = 86_400_000

/**
 * Horodatage stable pour la durée de vie du composant.
 *
 * `Date.now()` appelé directement pendant le rendu est une fonction impure :
 * deux rendus successifs peuvent produire des valeurs différentes, et deux
 * lignes d'une même liste peuvent être calculées sur des instants différents.
 * On fige donc la référence une seule fois par montage du composant.
 */
export function useNow(): number {
    const [now] = useState(() => Date.now())
    return now
}

/**
 * Nombre de jours (arrondi au supérieur) entre `now` et `date`.
 * Valeur positive = échéance future, négative = échéance dépassée.
 */
export function daysUntil(date: string | null | undefined, now: number): number {
    if (!date) return Number.NaN
    const target = new Date(date).getTime()
    if (Number.isNaN(target)) return Number.NaN
    return Math.ceil((target - now) / MS_PER_DAY)
}

/** Seuil métier ASECNA : l'évaluation de fin de période est déclenchée à J-14. */
export const EVALUATION_ALERT_DAYS = 14

/** True si l'échéance tombe dans la fenêtre d'alerte (J-14) et n'est pas dépassée. */
export function isWithinAlertWindow(daysLeft: number): boolean {
    return !Number.isNaN(daysLeft) && daysLeft <= EVALUATION_ALERT_DAYS && daysLeft > 0
}

/** Formate une date ISO en jj/mm/aaaa, ou '—' si absente/invalide. */
export function formatDate(date: string | null | undefined): string {
    if (!date) return '—'
    const d = new Date(date)
    return Number.isNaN(d.getTime()) ? '—' : d.toLocaleDateString('fr-FR')
}
