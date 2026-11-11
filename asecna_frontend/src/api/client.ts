import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'

/**
 * URL de base de l'API.
 *
 * Configurable via `VITE_API_BASE_URL` (fichier .env) : l'adresse
 * `http://127.0.0.1:8000` était codée en dur à trois endroits, ce qui rendait
 * tout déploiement hors poste de développement impossible.
 */
export const API_ROOT = (
    import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'
).replace(/\/+$/, '')

export const API_BASE = `${API_ROOT}/api/v1`

const api = axios.create({
    baseURL: API_BASE,
    headers: { 'Content-Type': 'application/json' },
})

// ─── Stockage des jetons ──────────────────────────────────────────────────────

const ACCESS_KEY = 'access_token'
const REFRESH_KEY = 'refresh_token'

export const tokenStore = {
    access: () => localStorage.getItem(ACCESS_KEY),
    refresh: () => localStorage.getItem(REFRESH_KEY),
    set(access: string, refresh?: string | null) {
        localStorage.setItem(ACCESS_KEY, access)
        // Le backend tourne avec ROTATE_REFRESH_TOKENS + BLACKLIST_AFTER_ROTATION :
        // chaque rafraîchissement renvoie un NOUVEAU refresh token et blackliste
        // l'ancien. L'ancienne version ne stockait que le access token, donc le
        // deuxième rafraîchissement réutilisait un jeton blacklisté et
        // déconnectait l'utilisateur. Il faut impérativement garder le nouveau.
        if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
    },
    clear() {
        localStorage.removeItem(ACCESS_KEY)
        localStorage.removeItem(REFRESH_KEY)
        localStorage.removeItem('user')
    },
}

/** Renvoie vers la page de connexion sans provoquer de boucle de redirection. */
function redirectToLogin() {
    tokenStore.clear()
    if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login'
    }
}

// ─── Requêtes : injection du jeton ────────────────────────────────────────────

api.interceptors.request.use((config) => {
    const token = tokenStore.access()
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    // Laisser le navigateur poser le bon Content-Type (avec boundary) pour FormData
    if (typeof FormData !== 'undefined' && config.data instanceof FormData) {
        delete config.headers['Content-Type']
    }
    return config
})

// ─── Réponses : rafraîchissement automatique du jeton ────────────────────────

type RetriableConfig = InternalAxiosRequestConfig & { _retry?: boolean }

/**
 * Un seul rafraîchissement à la fois : sans cette mutualisation, N requêtes
 * parallèles recevant 401 déclenchaient N appels à /token/refresh/, et la
 * rotation des jetons invalidait toutes les tentatives sauf la première.
 */
let refreshPromise: Promise<string> | null = null

function refreshAccessToken(): Promise<string> {
    if (refreshPromise) return refreshPromise

    const refresh = tokenStore.refresh()
    if (!refresh) return Promise.reject(new Error('no_refresh_token'))

    refreshPromise = axios
        .post(`${API_BASE}/auth/token/refresh/`, { refresh })
        .then((res) => {
            const { access, refresh: rotated } = res.data
            tokenStore.set(access, rotated)
            return access as string
        })
        .finally(() => {
            refreshPromise = null
        })

    return refreshPromise
}

api.interceptors.response.use(
    (res) => res,
    async (error: AxiosError) => {
        const original = error.config as RetriableConfig | undefined

        if (error.response?.status !== 401 || !original || original._retry) {
            return Promise.reject(error)
        }

        // Un 401 sur le rafraîchissement lui-même n'est pas rejouable
        if (original.url?.includes('/auth/token/refresh/')) {
            redirectToLogin()
            return Promise.reject(error)
        }

        original._retry = true
        try {
            const access = await refreshAccessToken()
            original.headers.Authorization = `Bearer ${access}`
            return api(original)
        } catch {
            redirectToLogin()
            return Promise.reject(error)
        }
    },
)

/**
 * Extrait un message lisible d'une erreur API.
 *
 * Le backend normalise ses erreurs en `{ error: { code, message, details } }`
 * via `core.exceptions.custom_exception_handler`. Les pages lisaient
 * `response.data.detail`, qui est toujours absent : tous les messages
 * d'erreur métier s'affichaient donc comme « ❌ Erreur ».
 */
export function apiErrorMessage(error: unknown, fallback = 'Une erreur est survenue.'): string {
    const data = (error as AxiosError<any>)?.response?.data as any
    if (!data) {
        const msg = (error as Error)?.message
        return msg && msg !== 'Network Error' ? msg : fallback
    }
    if (typeof data === 'string') return data
    if (data.error?.message) return data.error.message
    if (data.detail) return String(data.detail)
    // Erreurs de validation DRF brutes : { champ: ["message"] }
    const first = Object.entries(data)[0]
    if (first) {
        const [field, value] = first
        const text = Array.isArray(value) ? value[0] : value
        return field === 'non_field_errors' ? String(text) : `${field} : ${text}`
    }
    return fallback
}

export default api
