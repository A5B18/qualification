import { useState, useCallback, type ReactNode } from 'react'
import type { User, AuthTokens } from '../types'
import api, { tokenStore } from '../api/client'
import { AuthContext } from './authContextValue'

/**
 * Lecture de la session sauvegardée.
 *
 * Fait dans l'initialiseur de `useState` et non dans un `useEffect` : appeler
 * setState dans le corps d'un effet déclenche un second rendu en cascade
 * (et l'interface affichait brièvement l'écran de connexion à chaque
 * rechargement de page).
 */
function readStoredSession(): { user: User | null; tokens: AuthTokens | null } {
    try {
        const access = tokenStore.access()
        const refresh = tokenStore.refresh()
        const savedUser = localStorage.getItem('user')
        if (access && refresh && savedUser) {
            return { user: JSON.parse(savedUser) as User, tokens: { access, refresh } }
        }
    } catch {
        // Session corrompue (JSON invalide, stockage indisponible) : on repart à zéro
        tokenStore.clear()
    }
    return { user: null, tokens: null }
}

export function AuthProvider({ children }: { children: ReactNode }) {
    const [session, setSession] = useState(readStoredSession)
    const [isLoading, setIsLoading] = useState(false)

    const login = useCallback(async (matricule: string, password: string) => {
        setIsLoading(true)
        try {
            // Purger une éventuelle session expirée : un access token invalide
            // encore présent ferait échouer l'authentification de la requête
            // de connexion elle-même.
            tokenStore.clear()

            const res = await api.post('/auth/login/', { matricule, password })
            const { access, refresh } = res.data
            tokenStore.set(access, refresh)

            // Le profil complet (rôles, statut, is_admin, parcours) vient de /auth/me/
            const meRes = await api.get('/auth/me/')
            const userData = meRes.data as User

            localStorage.setItem('user', JSON.stringify(userData))
            setSession({ user: userData, tokens: { access, refresh } })
        } finally {
            setIsLoading(false)
        }
    }, [])

    const logout = useCallback(() => {
        const refresh = tokenStore.refresh()
        // Blacklister le refresh token côté serveur (best-effort : on déconnecte
        // l'utilisateur localement quoi qu'il arrive).
        if (refresh) {
            api.post('/auth/logout/', { refresh }).catch(() => undefined)
        }
        // `localStorage.clear()` effaçait aussi les préférences d'affichage
        // sans lien avec l'authentification : on ne retire que les clés de session.
        tokenStore.clear()
        setSession({ user: null, tokens: null })
    }, [])

    const updateUser = useCallback((newData: Partial<User>) => {
        setSession((prev) => {
            if (!prev.user) return prev
            const updated = { ...prev.user, ...newData }
            try {
                localStorage.setItem('user', JSON.stringify(updated))
            } catch {
                // Stockage indisponible : l'état mémoire reste correct
            }
            return { ...prev, user: updated }
        })
    }, [])

    /** Recharge le profil depuis le serveur (après changement de rôle par exemple). */
    const refreshProfile = useCallback(async () => {
        const res = await api.get('/auth/me/')
        const userData = res.data as User
        try {
            localStorage.setItem('user', JSON.stringify(userData))
        } catch {
            // ignoré
        }
        setSession((prev) => ({ ...prev, user: userData }))
    }, [])

    return (
        <AuthContext.Provider
            value={{
                user: session.user,
                tokens: session.tokens,
                login,
                logout,
                updateUser,
                refreshProfile,
                isLoading,
            }}
        >
            {children}
        </AuthContext.Provider>
    )
}
