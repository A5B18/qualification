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

    /** Blackliste le refresh token cote serveur. */
    logout: (refresh: string) => api.post('/auth/logout/', { refresh }),

    updateMe: (data: FormData | unknown) => api.patch('/auth/me/', data, {
        headers: data instanceof FormData ? { 'Content-Type': 'multipart/form-data' } : undefined
    }),

    /** Liste des utilisateurs (= agents) avec leurs profils */
    users: (params?: Record<string, string>) =>
        api.get('/auth/users/', { params }),

    user: (id: number) => api.get(`/auth/users/${id}/`),

    /** ADMIN : creer un compte agent */
    createUser: (data: {
        matricule: string; email: string; first_name: string
        last_name: string; phone?: string; password: string
    }) => api.post('/auth/users/', data),

    /** ADMIN : modifier l'identite d'un compte */
    updateUser: (id: number, data: unknown) => api.patch(`/auth/users/${id}/`, data),

    /** ADMIN : desactivation (suppression douce, is_active=false) */
    deactivateUser: (id: number) => api.delete(`/auth/users/${id}/`),

    /** ADMIN : attribuer un role fonctionnel */
    assignRole: (id: number, data: { role: string; notes?: string }) =>
        api.post(`/auth/users/${id}/assign-role/`, data),

    /** ADMIN : revoquer un role fonctionnel */
    revokeRole: (id: number, role: string) =>
        api.delete(`/auth/users/${id}/revoke-role/`, { data: { role } }),

    /**
     * ADMIN : reinitialiser le mot de passe.
     * Le mot de passe temporaire part par courriel ; il n'est renvoye dans la
     * reponse que si l'envoi n'a pas abouti (`delivered_by_email: false`).
     */
    resetPassword: (id: number) => api.post(`/auth/users/${id}/reset-password/`),

    /** Changer son propre mot de passe */
    changePassword: (data: { old_password: string; new_password: string }) =>
        api.put('/auth/change-password/', data),
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

    createSkill: (data: unknown) => api.post('/agents/skills/', data),
    deleteSkill: (id: number) => api.delete(`/agents/skills/${id}/`),
    createCertification: (data: unknown) => api.post('/agents/certifications/', data),
    deleteCertification: (id: number) => api.delete(`/agents/certifications/${id}/`),
    /** EVALUATEUR uniquement : noter un agent sur une annee */
    createPerformance: (data: unknown) => api.post('/agents/performances/', data),
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
    /** ADMIN : inscrire un agent a un stage */
    createInternship: (data: unknown) => api.post('/training/internships/', data),
    /** Cours e-learning — l'agent ne recoit que les cours publies */
    courses: (params?: Record<string, string>) =>
        api.get('/training/courses/', { params }),
    createCourse: (data: unknown) => api.post('/training/courses/', data),
    updateCourse: (id: number, data: unknown) =>
        api.patch(`/training/courses/${id}/`, data),
    deleteCourse: (id: number) => api.delete(`/training/courses/${id}/`),
    /** INSTRUCTEUR : rendre le cours visible des agents */
    publishCourse: (id: number) => api.post(`/training/courses/${id}/publish/`),
    unpublishCourse: (id: number) => api.post(`/training/courses/${id}/unpublish/`),
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
    /** Rattacher / detacher des questions : la relation est un ManyToMany */
    updateExam: (id: number, data: unknown) =>
        api.patch(`/evaluations/exams/${id}/`, data),
    publishExam: (id: number) => api.post(`/evaluations/exams/${id}/publish/`),
    unpublishExam: (id: number) => api.post(`/evaluations/exams/${id}/unpublish/`),
    /** Enonces de l'examen — sans le corrige pour un agent */
    examQuestions: (id: number) => api.get(`/evaluations/exams/${id}/questions/`),

    /** Banque de questions */
    questions: (params?: Record<string, string>) =>
        api.get('/evaluations/questions/', { params }),
    createQuestion: (data: unknown) => api.post('/evaluations/questions/', data),
    updateQuestion: (id: number, data: unknown) =>
        api.patch(`/evaluations/questions/${id}/`, data),
    deleteQuestion: (id: number) => api.delete(`/evaluations/questions/${id}/`),
    startSession: (examId: number) =>
        api.post(`/evaluations/exams/${examId}/start-session/`),
    sessions: (params?: Record<string, string>) =>
        api.get('/evaluations/sessions/', { params }),
    session: (id: number) => api.get(`/evaluations/sessions/${id}/`),
    /**
     * Copie de l'agent : une entree par reponse, avec son bareme, sa
     * correction eventuelle et — pour un correcteur — la reponse attendue.
     * Renvoie aussi `unanswered`, les questions laissees vides (elles comptent
     * pour 0 dans le score).
     */
    sessionAnswers: (id: number) => api.get(`/evaluations/sessions/${id}/answers/`),
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

export const workflowsApi = {
    /**
     * Registre transversal des approbations : une ligne par objet soumis,
     * tous modules confondus (rapports, mentorats, corrections d'examen).
     */
    list: (params?: Record<string, string>) =>
        api.get('/workflows/', { params }),
    /** Ce qui attend une décision — réservé aux décideurs */
    pending: (params?: Record<string, string>) =>
        api.get('/workflows/pending/', { params }),
    approve: (id: number, data?: { approver_comment?: string; unit_chief_comment?: string }) =>
        api.post(`/workflows/${id}/approve/`, data ?? {}),
    /** Le motif est obligatoire côté serveur */
    reject: (id: number, data: { approver_comment: string }) =>
        api.post(`/workflows/${id}/reject/`, data),
}

export const auditApi = {
    logs: (params?: Record<string, string>) =>
        api.get('/audit/logs/', { params }),
    /** Historique des connexions — la route backend est /audit/logins/ */
    loginHistory: (params?: Record<string, string>) =>
        api.get('/audit/logins/', { params }),
}

