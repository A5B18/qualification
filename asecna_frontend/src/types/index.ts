// Types TypeScript pour ASECNA Career Management

export interface User {
    id: number
    matricule: string
    email: string
    first_name: string
    last_name: string
    full_name: string
    is_active?: boolean
    is_staff?: boolean
    is_superuser?: boolean
    /** Rôles fonctionnels de l'agent (ex: ['EVALUATOR', 'UNIT_CHIEF']) */
    roles?: string[]
    /** True si is_superuser ou rôle ADMIN */
    is_admin?: boolean
    /**
     * Statut de parcours renvoyé par l'API (`status`).
     * `agent_status` est conservé comme alias historique : l'API ne l'a jamais
     * renvoyé, c'est `status` qui porte la valeur.
     */
    status?: AgentStatus | null
    /** @deprecated L'API renvoie `status`. */
    agent_status?: string
    /** ID de l'unité d'affectation (issu du profil agent) */
    unit?: number | null
    unit_detail?: Unit | null
    /** Parcours professionnel imbriqué (null si l'agent n'a pas de profil) */
    agent_profile?: AgentProfile | null
    hire_date?: string | null
    qualification_date?: string | null
    /** URL de la photo de profil si présente */
    photo?: string | null
    date_joined?: string
}

export interface AuthTokens {
    access: string
    refresh: string
}

export interface AgentProfile {
    id: number
    user: number
    status: AgentStatus
    unit: number | null
    unit_detail?: Unit
    specialty: number | null
    specialty_detail?: Specialty
    hire_date: string | null
    qualification_date: string | null
    notes: string
}

export type AgentStatus = 'NEW' | 'PROBATION' | 'MENTORED' | 'TRAINEE' | 'QUALIFIED' | 'SUSPENDED' | 'RETIRED'

export const AgentStatusLabels: Record<AgentStatus, string> = {
    NEW: 'Nouveau',
    PROBATION: "En période d'essai",
    MENTORED: 'En mentorat',
    TRAINEE: 'En formation',
    QUALIFIED: 'Qualifié',
    SUSPENDED: 'Suspendu',
    RETIRED: 'Retraité',
}

export const AgentStatusColors: Record<AgentStatus, string> = {
    NEW: 'bg-gray-100 text-gray-700',
    PROBATION: 'bg-yellow-100 text-yellow-700',
    MENTORED: 'bg-blue-100 text-blue-700',
    TRAINEE: 'bg-purple-100 text-purple-700',
    QUALIFIED: 'bg-green-100 text-green-700',
    SUSPENDED: 'bg-red-100 text-red-700',
    RETIRED: 'bg-gray-200 text-gray-600',
}

export interface Unit {
    id: number
    code: string
    name: string
    unit_type: string
    location: string
    country: string
    description: string
    is_active: boolean
}

export interface Specialty {
    id: number
    code: string
    name: string
    description: string
    is_active: boolean
}

export type ProbationStatus = 'IN_PROGRESS' | 'PASSED' | 'FAILED' | 'CANCELLED'

export const ProbationStatusLabels: Record<ProbationStatus, string> = {
    IN_PROGRESS: 'En cours',
    PASSED: 'Réussi',
    FAILED: 'Échoué',
    CANCELLED: 'Annulé',
}

export const ProbationStatusColors: Record<ProbationStatus, string> = {
    IN_PROGRESS: 'bg-blue-100 text-blue-700',
    PASSED: 'bg-green-100 text-green-700',
    FAILED: 'bg-red-100 text-red-700',
    CANCELLED: 'bg-gray-100 text-gray-700',
}

export interface ProbationPeriod {
    id: number
    agent: number
    agent_detail?: User
    attempt_number: number
    start_date: string
    end_date: string
    actual_end_date: string | null
    probation_status: ProbationStatus
    unit_chief_comment: string
    mentor_comment: string
    created_at: string
    /** Note /100 saisie par l'évaluateur (null tant que non finalisée) */
    score?: string | number | null
    is_last_attempt?: boolean
    is_renewable?: boolean
    evaluated_by?: number | null
    evaluated_by_detail?: Partial<User> | null
}

export type MentoringStatus = 'DRAFT' | 'SUBMITTED' | 'APPROVED' | 'REJECTED' | 'COMPLETED'

export const MentoringStatusLabels: Record<MentoringStatus, string> = {
    DRAFT: 'Brouillon',
    SUBMITTED: "Soumis au chef d'unité",
    APPROVED: 'Approuvé',
    REJECTED: 'Rejeté',
    COMPLETED: 'Terminé',
}

export const MentoringStatusColors: Record<MentoringStatus, string> = {
    DRAFT: 'bg-gray-100 text-gray-700',
    SUBMITTED: 'bg-yellow-100 text-yellow-700',
    APPROVED: 'bg-green-100 text-green-700',
    REJECTED: 'bg-red-100 text-red-700',
    COMPLETED: 'bg-blue-100 text-blue-700',
}

export interface MentoringRecord {
    id: number
    agent: number
    agent_detail?: User
    mentor: number
    mentor_detail?: User
    unit_chief?: number
    start_date: string
    end_date: string | null
    objectives: string
    mentor_observations: string
    mentor_opinion: string
    unit_chief_opinion: string
    mentoring_status: MentoringStatus
    submitted_at: string | null
    approved_at: string | null
    created_at: string
}

export type ReportType = 'PROBATION' | 'MENTORING' | 'ASSESSMENT'
export type ReportStatus = 'DRAFT' | 'SUBMITTED' | 'APPROVED' | 'REJECTED'

export const ReportTypeLabels: Record<ReportType, string> = {
    PROBATION: "Rapport de période d'essai",
    MENTORING: 'Rapport de mentorat',
    ASSESSMENT: 'Bilan périodique',
}

export const ReportStatusLabels: Record<ReportStatus, string> = {
    DRAFT: 'Brouillon',
    SUBMITTED: 'Soumis',
    APPROVED: 'Approuvé',
    REJECTED: 'Rejeté',
}

export const ReportStatusColors: Record<ReportStatus, string> = {
    DRAFT: 'bg-gray-100 text-gray-700',
    SUBMITTED: 'bg-yellow-100 text-yellow-700',
    APPROVED: 'bg-green-100 text-green-700',
    REJECTED: 'bg-red-100 text-red-700',
}

export interface Report {
    id: number
    report_type: ReportType
    agent: number
    agent_detail?: User
    created_by: number
    title: string
    content: string
    conclusion: string
    report_status: ReportStatus
    submitted_at: string | null
    approved_at: string | null
    created_at: string
}

export interface ARCEPBook {
    id: number
    agent: number
    agent_detail?: User
    opened_at: string
    is_active: boolean
    entries?: ARCEPEntry[]
}

export interface ARCEPEntry {
    id: number
    book: number
    entry_date: string
    activity: string
    duration_hours: number
    notes: string
    created_at: string
    /** True si l'entrée est couverte par une signature du chef d'unité */
    is_validated?: boolean
    agent_detail?: Partial<User> | null
}

export interface ARCEPSignature {
    id: number
    book: number
    unit_chief: number | null
    unit_chief_detail?: Partial<User> | null
    period_start: string
    period_end: string
    comment: string
    signed_at: string
    covered_entries_count?: number
}

export interface Training {
    id: number
    title: string
    specialty: number | null
    specialty_detail?: Specialty
    training_type: string
    description: string
    duration_days: number
    passing_score: number
    is_active: boolean
}

export interface AuditLog {
    id: number
    user: number | null
    user_detail?: User
    action: string
    endpoint: string
    status_code: number
    ip_address: string
    timestamp: string
}

export interface PaginatedResponse<T> {
    count: number
    next: string | null
    previous: string | null
    results: T[]
}
