/**
 * Fonctions API Axios pour tous les modules ASECNA.
 *
 * Endpoints backend réels (basés sur les urls.py Django) :
 *   /auth/login/           → JWT login
 *   /auth/token/refresh/   → JWT refresh
 *   /auth/me/              → profil courant
 *   /auth/users/           → liste utilisateurs (inclut les profils agents)
 *   /units/                → unités
 *   /agents/skills/        → compétences
 *   /agents/certifications/→ certifications
 *   /agents/performances/  → indicateurs
 *   /probation/            → périodes d'essai
 *   /mentoring/            → fiches de mentorat
 *   /reports/              → rapports
 *   /arcep/books/          → carnets ARCEP
 *   /arcep/entries/        → entrées ARCEP
 *   /arcep/signatures/     → signatures
 *   /training/specialties/ → spécialités
 *   /training/trainings/   → formations
 *   /training/internships/ → stages
 *   /evaluations/exams/    → examens
 *   /evaluations/sessions/ → sessions
 *   /audit/logs/           → logs d'audit
 *   /audit/logins/         → historique connexions
 */

import api from './client'

export const authApi = {
    login: (matricule: string, password: string) =>
        api.post('/auth/login/', { matricule, password }),

    refresh: (refresh: string) =>
        api.post('/auth/token/refresh/', { refresh }),

    me: () => api.get('/auth/me/'),

    updateMe: (data: FormData | unknown) => api.patch('/auth/me/', data, {
        headers: data instanceof FormData ? { 'Content-Type': 'multipart/form-data' } : undefined
    }),

    /** Liste des utilisateurs (= agents) avec leurs profils */
    users: (params?: Record<string, string>) =>
        api.get('/auth/users/', { params }),

    user: (id: number) => api.get(`/auth/users/${id}/`),
}

// Alias pour la compatibilité avec les pages agents
export const agentsApi = {
    /** Liste des agents = utilisateurs avec profil */
    list: (params?: Record<string, string>) =>
        api.get('/auth/users/', { params }),

    get: (id: number) => api.get(`/auth/users/${id}/`),

    /** Pas d'endpoint /agents/profiles/ — on utilise /auth/users/ */
    profiles: (params?: Record<string, string>) =>
        api.get('/auth/users/', { params }),

    profile: (id: number) => api.get(`/auth/users/${id}/`),

    skills: (params?: Record<string, string>) =>
        api.get('/agents/skills/', { params }),

    certifications: (params?: Record<string, string>) =>
        api.get('/agents/certifications/', { params }),

    performances: (params?: Record<string, string>) =>
        api.get('/agents/performances/', { params }),
}

export const unitsApi = {
    list: (params?: Record<string, string>) =>
        api.get('/units/', { params }),
    get: (id: number) => api.get(`/units/${id}/`),
    /** Agents d'une unité — filtrés côté serveur via ?unit= */
    agents: (id: number) =>
        api.get('/auth/users/', { params: { unit: String(id), page_size: '200' } }),
}

export const probationApi = {
    list: (params?: Record<string, string>) =>
        api.get('/probation/', { params }),
    get: (id: number) => api.get(`/probation/${id}/`),
    create: (data: unknown) => api.post('/probation/', data),
    update: (id: number, data: unknown) => api.patch(`/probation/${id}/`, data),
    /** EVALUATEUR : saisir le score final → PASSED ou FAILED */
    finalize: (id: number, data: { score: number; unit_chief_comment?: string }) =>
        api.post(`/probation/${id}/finalize/`, data),
    /** Liste des périodes à évaluer dans 14 jours */
    evaluationDue: () => api.get('/probation/evaluation-due/'),
}

export const mentoringApi = {
    list: (params?: Record<string, string>) =>
        api.get('/mentoring/', { params }),
    get: (id: number) => api.get(`/mentoring/${id}/`),
    create: (data: unknown) => api.post('/mentoring/', data),
    submit: (id: number, data: unknown) => api.post(`/mentoring/${id}/submit/`, data),
    approve: (id: number, data: unknown) =>
        api.post(`/mentoring/${id}/approve/`, data),
    reject: (id: number, data: unknown) =>
        api.post(`/mentoring/${id}/reject/`, data),
}

export const reportsApi = {
    list: (params?: Record<string, string>) =>
        api.get('/reports/', { params }),
    get: (id: number) => api.get(`/reports/${id}/`),
    create: (data: unknown) => api.post('/reports/', data),
    submit: (id: number) => api.post(`/reports/${id}/submit/`),
    approve: (id: number, data: unknown) =>
        api.post(`/reports/${id}/approve/`, data),
    reject: (id: number, data: unknown) =>
        api.post(`/reports/${id}/reject/`, data),
}

export const arcepApi = {
    books: (params?: Record<string, string>) =>
        api.get('/arcep/books/', { params }),
    book: (id: number) => api.get(`/arcep/books/${id}/`),
    entries: (bookId: number) =>
        api.get('/arcep/entries/', { params: { book: String(bookId) } }),
    allEntries: (params?: Record<string, string>) =>
        api.get('/arcep/entries/', { params }),
    createEntry: (data: unknown) => api.post('/arcep/entries/', data),
    signatures: (bookId: number) =>
        api.get('/arcep/signatures/', { params: { book: String(bookId) } }),
    /**
     * Signer une période du carnet.
     *
     * Le modèle attend `period_start` / `period_end` et un `comment`.
     * L'ancien appel envoyait `{ book, notes }` : la signature échouait en 400
     * (champs de période obligatoires) et `notes` n'existe pas sur le modèle.
     * Si la période est omise, le backend la déduit des entrées non signées.
     */
    createSignature: (data: {
        book: number
        period_start?: string
        period_end?: string
        comment?: string
    }) => api.post('/arcep/signatures/', data),
    coveredEntries: (signatureId: number) =>
        api.get(`/arcep/signatures/${signatureId}/covered-entries/`),
}

export const trainingApi = {
    specialties: (params?: Record<string, string>) =>
        api.get('/training/specialties/', { params }),
    trainings: (params?: Record<string, string>) =>
        api.get('/training/trainings/', { params }),
    internships: (params?: Record<string, string>) =>
        api.get('/training/internships/', { params }),
    /** Maintiens de qualification */
    maintenances: (params?: Record<string, string>) =>
        api.get('/training/maintenances/', { params }),
    maintenance: (id: number) => api.get(`/training/maintenances/${id}/`),
    /** EVALUATEUR : saisir le score → PASSED (≥70) ou FAILED (suspension agent) */
    finalizeMaintenace: (id: number, data: { score: number; notes?: string }) =>
        api.post(`/training/maintenances/${id}/finalize/`, data),
    /** UNIT_CHIEF : dispenser l'agent */
    waiveMaintenance: (id: number, data: { notes?: string }) =>
        api.post(`/training/maintenances/${id}/waive/`, data),
    /** Contrôles en retard (due_date dépassée) */
    overdueMaintenances: () => api.get('/training/maintenances/overdue/'),
}

export const evaluationsApi = {
    exams: (params?: Record<string, string>) =>
        api.get('/evaluations/exams/', { params }),
    create: (data: unknown) => api.post('/evaluations/exams/', data),
    exam: (id: number) => api.get(`/evaluations/exams/${id}/`),
    startSession: (examId: number) =>
        api.post(`/evaluations/exams/${examId}/start-session/`),
    sessions: (params?: Record<string, string>) =>
        api.get('/evaluations/sessions/', { params }),
    session: (id: number) => api.get(`/evaluations/sessions/${id}/`),
    /** Agent soumet une réponse */
    submitAnswer: (sessionId: number, data: { question: number; response: string }) =>
        api.post(`/evaluations/sessions/${sessionId}/submit-answer/`, data),
    /** Agent finalise sa copie → SUBMITTED */
    finalizeSession: (sessionId: number) =>
        api.post(`/evaluations/sessions/${sessionId}/finalize/`),
    /** EVALUATEUR : corriger une réponse (grade-answer) */
    gradeAnswer: (sessionId: number, data: {
        answer_id: number; is_correct: boolean;
        evaluator_score: number; feedback?: string
    }) => api.post(`/evaluations/sessions/${sessionId}/grade-answer/`, data),
    /** EVALUATEUR : soumettre la correction au chef */
    submitForApproval: (sessionId: number) =>
        api.post(`/evaluations/sessions/${sessionId}/submit-for-approval/`),
    /** UNIT_CHIEF : approuver la correction */
    approveSession: (sessionId: number) =>
        api.post(`/evaluations/sessions/${sessionId}/approve/`),
    /** UNIT_CHIEF : rejeter avec motif obligatoire */
    rejectSession: (sessionId: number, data: { reason: string }) =>
        api.post(`/evaluations/sessions/${sessionId}/reject/`, data),
}

export const auditApi = {
    logs: (params?: Record<string, string>) =>
        api.get('/audit/logs/', { params }),
    /** Historique des connexions — la route backend est /audit/logins/ */
    loginHistory: (params?: Record<string, string>) =>
        api.get('/audit/logins/', { params }),
}

