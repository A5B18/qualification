/**
 * Tests de la couche HTTP.
 *
 * Deux comportements s'y jouaient sans filet :
 *   • la taille de page demandée par défaut — son absence tronquait
 *     silencieusement toutes les listes à 20 éléments ;
 *   • la lecture du message d'erreur métier — le backend normalise ses erreurs
 *     en `{ error: { code, message } }`, et lire `detail` affichait « Erreur »
 *     à la place de la règle métier violée.
 */

import { describe, it, expect } from 'vitest'
import { AxiosHeaders, type InternalAxiosRequestConfig } from 'axios'

import api, { apiErrorMessage, DEFAULT_PAGE_SIZE } from './client'

/** Rejoue l'intercepteur de requête sur une configuration donnée. */
function runRequestInterceptor(
    config: Partial<InternalAxiosRequestConfig>,
): InternalAxiosRequestConfig {
    // Le premier intercepteur enregistré est celui qui nous intéresse.
    const handler = (api.interceptors.request as unknown as {
        handlers: { fulfilled: (c: InternalAxiosRequestConfig) => InternalAxiosRequestConfig }[]
    }).handlers[0]
    const full = {
        headers: new AxiosHeaders(),
        method: 'get',
        ...config,
    } as InternalAxiosRequestConfig
    return handler.fulfilled(full)
}

describe('taille de page par défaut', () => {
    it('ajoute page_size aux GET qui n’en précisent pas', () => {
        const config = runRequestInterceptor({ url: '/auth/users/' })
        expect(config.params).toMatchObject({ page_size: String(DEFAULT_PAGE_SIZE) })
    })

    it('respecte une taille de page choisie par l’appelant', () => {
        const config = runRequestInterceptor({
            url: '/auth/users/', params: { page_size: '10' },
        })
        expect(config.params.page_size).toBe('10')
    })

    it('ne force rien quand une page précise est demandée', () => {
        const config = runRequestInterceptor({ url: '/auth/users/', params: { page: '2' } })
        expect(config.params.page_size).toBeUndefined()
    })

    it('laisse les POST intacts', () => {
        const config = runRequestInterceptor({ url: '/probation/', method: 'post' })
        expect(config.params).toBeUndefined()
    })

    it('conserve les filtres déjà posés', () => {
        const config = runRequestInterceptor({
            url: '/arcep/entries/', params: { book: '3' },
        })
        expect(config.params).toMatchObject({
            book: '3', page_size: String(DEFAULT_PAGE_SIZE),
        })
    })

    it('reste sous le plafond serveur de 500', () => {
        expect(DEFAULT_PAGE_SIZE).toBeLessThanOrEqual(500)
    })
})

describe('apiErrorMessage', () => {
    it('lit le message métier normalisé par le backend', () => {
        const message = apiErrorMessage({
            response: {
                data: {
                    error: {
                        code: 'bad_request',
                        message: 'La durée doit être approximativement de 3 mois.',
                    },
                },
            },
        })
        expect(message).toBe('La durée doit être approximativement de 3 mois.')
    })

    it('accepte le `detail` de DRF', () => {
        expect(apiErrorMessage({ response: { data: { detail: 'Non trouvé.' } } }))
            .toBe('Non trouvé.')
    })

    it('déplie une erreur de validation par champ', () => {
        expect(apiErrorMessage({
            response: { data: { score: ['Score entre 0 et 100.'] } },
        })).toBe('score : Score entre 0 et 100.')
    })

    it('ne préfixe pas les erreurs non liées à un champ', () => {
        expect(apiErrorMessage({
            response: { data: { non_field_errors: ['Les dates se chevauchent.'] } },
        })).toBe('Les dates se chevauchent.')
    })

    it('retombe sur le message fourni quand la réponse est vide', () => {
        expect(apiErrorMessage(new Error('Network Error'), 'Serveur injoignable.'))
            .toBe('Serveur injoignable.')
    })
})
