import { createContext, useContext } from 'react'
import type { User, AuthTokens } from '../types'

export interface AuthContextType {
    user: User | null
    tokens: AuthTokens | null
    login: (matricule: string, password: string) => Promise<void>
    logout: () => void
    updateUser: (newData: Partial<User>) => void
    refreshProfile: () => Promise<void>
    isLoading: boolean
}

/**
 * Contexte d'authentification.
 *
 * Isolé du composant `AuthProvider` : un module qui exporte autre chose que
 * des composants casse le Fast Refresh de Vite (règle
 * `react-refresh/only-export-components`).
 */
export const AuthContext = createContext<AuthContextType | null>(null)

export function useAuth(): AuthContextType {
    const ctx = useContext(AuthContext)
    if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
    return ctx
}
