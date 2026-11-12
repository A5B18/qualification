/**
 * Règle métier J-14 : l'évaluation de fin de période d'essai se déclenche
 * quatorze jours avant l'échéance. Le tableau de bord de l'évaluateur et la
 * liste des probations surlignent les périodes concernées à partir de ces
 * fonctions.
 */

import { describe, it, expect } from 'vitest'
import { daysUntil, isWithinAlertWindow, formatDate, EVALUATION_ALERT_DAYS } from './dates'

const MS_PER_DAY = 86_400_000
const NOW = new Date('2026-06-01T12:00:00Z').getTime()

function inDays(n: number): string {
    return new Date(NOW + n * MS_PER_DAY).toISOString()
}

describe('daysUntil', () => {
    it('compte les jours restants avant une échéance future', () => {
        expect(daysUntil(inDays(10), NOW)).toBe(10)
    })

    it('renvoie une valeur négative pour une échéance dépassée', () => {
        expect(daysUntil(inDays(-3), NOW)).toBe(-3)
    })

    it('renvoie NaN quand la date est absente ou invalide', () => {
        expect(daysUntil(null, NOW)).toBeNaN()
        expect(daysUntil('pas une date', NOW)).toBeNaN()
    })
})

describe('fenêtre d’alerte J-14', () => {
    it('vaut bien quatorze jours', () => {
        expect(EVALUATION_ALERT_DAYS).toBe(14)
    })

    it('signale une échéance à J-10', () => {
        expect(isWithinAlertWindow(daysUntil(inDays(10), NOW))).toBe(true)
    })

    it('signale encore une échéance pile à J-14', () => {
        expect(isWithinAlertWindow(14)).toBe(true)
    })

    it('ne signale pas une échéance à J-15', () => {
        expect(isWithinAlertWindow(15)).toBe(false)
    })

    it('ne signale pas une échéance déjà dépassée', () => {
        // Une période close relève du retard, pas de l'alerte anticipée.
        expect(isWithinAlertWindow(0)).toBe(false)
        expect(isWithinAlertWindow(-2)).toBe(false)
    })

    it('ne signale rien quand la date est inconnue', () => {
        expect(isWithinAlertWindow(Number.NaN)).toBe(false)
    })
})

describe('formatDate', () => {
    it('formate en jj/mm/aaaa', () => {
        expect(formatDate('2026-03-09')).toBe('09/03/2026')
    })

    it('affiche un tiret plutôt qu’une date invalide', () => {
        expect(formatDate(null)).toBe('—')
        expect(formatDate('')).toBe('—')
        expect(formatDate('n’importe quoi')).toBe('—')
    })
})
