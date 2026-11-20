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
    /**
     * Alias servis par `UserSerializer` pour la liste des agents : la page
     * navigue vers /agents/<user> et lit l'identité dans `user_detail`.
     */
    user?: number
    user_detail?: {
        id: number
        matricule: string
        first_name: string
        last_name: string
        full_name: string
        email: string
    }
    specialty_detail?: Specialty | null
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
    PROBATION: 'bg-warning-100 text-warning-700',
    MENTORED: 'bg-info-100 text-info-700',
    TRAINEE: 'bg-accent-100 text-accent-700',
    QUALIFIED: 'bg-success-100 text-success-700',
    SUSPENDED: 'bg-danger-100 text-danger-700',
    RETIRED: 'bg-gray-200 text-gray-600',
}

/**
 * Couleurs des sept statuts pour les graphiques.
 *
 * Recharts peint ses barres en CSS inline : il lui faut une valeur, pas une
 * classe utilitaire. Ces teintes sont les nuances 500 des mêmes familles que
 * `AgentStatusColors`, afin qu'une barre et la pastille correspondante
 * portent la même couleur.
 *
 * Le tableau de bord redéfinissait sa propre liste de statuts : c'est ainsi
 * que « Retraité » avait été oublié et que le graphique n'en montrait que
 * six. Toute barre se dérive désormais de `AgentStatusLabels`, qui couvre les
 * sept par construction.
 */
export const AgentStatusChartColors: Record<AgentStatus, string> = {
    NEW: '#64748b',        // ardoise 500
    PROBATION: '#f59e0b',  // ambre 500
    MENTORED: '#0284c7',   // ciel 500
    TRAINEE: '#8b5cf6',    // violet 500
    QUALIFIED: '#10b981',  // émeraude 500
    SUSPENDED: '#ef4444',  // rouge 500
    RETIRED: '#cbd5e1',    // ardoise 300
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
    IN_PROGRESS: 'bg-info-100 text-info-700',
    PASSED: 'bg-success-100 text-success-700',
    FAILED: 'bg-danger-100 text-danger-700',
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
    SUBMITTED: 'bg-warning-100 text-warning-700',
    APPROVED: 'bg-success-100 text-success-700',
    REJECTED: 'bg-danger-100 text-danger-700',
    COMPLETED: 'bg-info-100 text-info-700',
}

export interface MentoringRecord {
    id: number
    agent: number
    agent_detail?: User
    mentor: number
    mentor_detail?: User
    unit_chief?: number
    unit_chief_detail?: User | null
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
    SUBMITTED: 'bg-warning-100 text-warning-700',
    APPROVED: 'bg-success-100 text-success-700',
    REJECTED: 'bg-danger-100 text-danger-700',
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
    created_by_detail?: { id: number; full_name?: string; first_name?: string; last_name?: string } | null
}

/** Statuts d'une qualification, tels que le backend les calcule. */
export type QualificationStatus =
    | 'VALID' | 'EXPIRING' | 'EXPIRED'
    | 'PENDING' | 'OVERDUE' | 'PASSED'
    | 'FAILED' | 'WAIVED' | 'PERMANENT'

export const QualificationStatusLabels: Record<QualificationStatus, string> = {
    VALID: 'Valide',
    EXPIRING: 'Échéance proche',
    EXPIRED: 'Expirée',
    PENDING: 'Contrôle à venir',
    OVERDUE: 'Contrôle en retard',
    PASSED: 'Contrôle réussi',
    FAILED: 'Échec — agent suspendu',
    WAIVED: "Dispense du chef d'unité",
    PERMANENT: 'Sans échéance',
}

export const QualificationStatusColors: Record<QualificationStatus, string> = {
    VALID: 'bg-success-100 text-success-700',
    EXPIRING: 'bg-warning-100 text-warning-700',
    EXPIRED: 'bg-danger-100 text-danger-700',
    PENDING: 'bg-info-100 text-info-700',
    OVERDUE: 'bg-danger-100 text-danger-700',
    PASSED: 'bg-success-100 text-success-700',
    FAILED: 'bg-danger-100 text-danger-700',
    WAIVED: 'bg-gray-100 text-gray-600',
    PERMANENT: 'bg-gray-100 text-gray-600',
}

/** Origine d'une qualification dans le carnet. */
export type QualificationKind = 'CERTIFICATION' | 'MAINTENANCE' | 'INTERNSHIP'

/** Une ligne du tableau « qualifications et échéances » du carnet ARCEP. */
export interface ARCEPQualification {
    kind: QualificationKind
    kind_label: string
    label: string
    issuer: string
    obtained_on: string | null
    due_date: string | null
    /** `due_date` est-elle une échéance encore à tenir ? */
    tracks_due: boolean
    status: QualificationStatus
    status_label: string
    days_remaining: number | null
    score: string | null
    note: string
}

export interface ARCEPQualificationsSummary {
    total: number
    valid: number
    expiring_soon: number
    expired: number
    waived: number
    next_due_date: string | null
    next_due_label: string | null
    next_due_in_days: number | null
    alert_level: 'OK' | 'WARNING' | 'CRITICAL'
    warning_window_days: number
}

/** En-tête du carnet : qui est le titulaire. */
export interface ARCEPAgentIdentity {
    id: number
    matricule: string
    last_name: string
    first_name: string
    full_name: string
    email: string
    phone: string
    photo: string | null
    /** Spécialité technique du profil agent — la profession exercée. */
    profession: string | null
    profession_code: string | null
    roles: string[]
    career_status: AgentStatus | null
    career_status_label: string | null
    unit: {
        id: number
        code: string
        name: string
        unit_type: string
        unit_type_label: string
        location: string
        country: string
    } | null
    hire_date: string | null
    qualification_date: string | null
    seniority_years: number | null
}

export interface ARCEPBook {
    id: number
    agent: number
    agent_detail?: User
    opened_at: string
    is_active: boolean
    entries?: ARCEPEntry[]
    /** Total d'heures du carnet, calcule par le serializer. */
    total_hours?: string | number
    entries_count?: number
    /** Première page du carnet : identité du titulaire. */
    agent_identity?: ARCEPAgentIdentity | null
    /** Qualifications et échéances, la plus urgente en tête. */
    qualifications?: ARCEPQualification[]
    qualifications_summary?: ARCEPQualificationsSummary
    signatures_count?: number
    /** Fin de la dernière période visée par le chef d'unité. */
    last_signed_on?: string | null
    /** Entrées qui attendent encore le visa du chef d'unité. */
    pending_signature_count?: number
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

// ─── Evaluations ──────────────────────────────────────────────────────────────

export type QuestionType = 'GENERAL' | 'TECHNICAL' | 'UNIT_SPECIFIC'

/**
 * Le QCM est le seul format d'évaluation (backend : migration 0003).
 * Le Vrai/Faux n'était qu'un QCM à deux options, et une réponse libre ne se
 * corrige pas de façon reproductible.
 */
export type QuestionKind = 'MCQ'

/** Bornes du nombre de propositions, alignées sur `Question.MIN/MAX_OPTIONS`. */
export const MCQ_MIN_OPTIONS = 2
export const MCQ_MAX_OPTIONS = 6

export const QuestionTypeLabels: Record<QuestionType, string> = {
    GENERAL: 'Généralités',
    TECHNICAL: 'Technique',
    UNIT_SPECIFIC: "Spécifique à l'unité",
}

export const QuestionKindLabels: Record<QuestionKind, string> = {
    MCQ: 'QCM',
}

export interface Question {
    id: number
    training?: number | null
    question_type: QuestionType
    question_kind: QuestionKind
    text: string
    difficulty: number
    /** Absent de la version servie au candidat pendant la composition. */
    correct_answer?: string
    options: string[]
    points: number
    created_by_name?: string | null
    is_active?: boolean
}

export type ExamStatus = 'DRAFT' | 'PUBLISHED' | 'CLOSED'

export const ExamStatusLabels: Record<ExamStatus, string> = {
    DRAFT: 'Brouillon',
    PUBLISHED: 'Publié',
    CLOSED: 'Fermé',
}

export const ExamStatusColors: Record<ExamStatus, string> = {
    DRAFT: 'bg-gray-100 text-gray-700',
    PUBLISHED: 'bg-success-100 text-success-700',
    CLOSED: 'bg-danger-100 text-danger-700',
}

export interface Exam {
    id: number
    title: string
    training: number | null
    training_detail?: { id: number; title: string } | null
    questions?: number[]
    questions_count?: number
    duration_minutes: number
    passing_score: number
    exam_status: ExamStatus
    created_by_name?: string | null
    created_at?: string
}

export type SessionStatus =
    | 'IN_PROGRESS' | 'SUBMITTED' | 'CORRECTING'
    | 'PENDING_APPROVAL' | 'GRADED' | 'REJECTED'

export const SessionStatusLabels: Record<SessionStatus, string> = {
    IN_PROGRESS: 'En cours',
    SUBMITTED: 'Soumise — à corriger',
    CORRECTING: 'En correction',
    PENDING_APPROVAL: 'Correction à valider',
    GRADED: 'Corrigée et validée',
    REJECTED: 'Correction rejetée',
}

export const SessionStatusColors: Record<SessionStatus, string> = {
    IN_PROGRESS: 'bg-gray-100 text-gray-700',
    SUBMITTED: 'bg-warning-100 text-warning-700',
    CORRECTING: 'bg-info-100 text-info-700',
    PENDING_APPROVAL: 'bg-accent-100 text-accent-700',
    GRADED: 'bg-success-100 text-success-700',
    REJECTED: 'bg-danger-100 text-danger-700',
}

export interface ExamSession {
    id: number
    exam: number
    exam_detail?: { id: number; title: string; passing_score: number } | null
    agent: number
    agent_detail?: {
        id: number; matricule: string; first_name: string; last_name: string
    } | null
    session_status: SessionStatus
    score: string | number | null
    is_passed: boolean | null
    started_at?: string
    submitted_at?: string | null
    graded_at?: string | null
    approved_at?: string | null
    graded_by_detail?: { id: number; first_name: string; last_name: string } | null
    approved_by_detail?: { id: number; first_name: string; last_name: string } | null
    rejection_reason?: string
    /** Avancement de la correction, calculé côté serveur. */
    answers_count?: number
    corrected_count?: number
    pending_correction_count?: number
}

export interface Answer {
    id: number
    session: number
    question: number
    question_detail?: {
        id: number
        text: string
        question_type: QuestionType
        points: number
        /** Ajouté uniquement pour les profils habilités à corriger. */
        correct_answer?: string
        question_kind?: QuestionKind
        options?: string[]
    } | null
    response: string
    evaluator_score: string | number | null
    is_correct: boolean | null
    feedback: string
    corrected_by_detail?: { id: number; first_name: string; last_name: string } | null
    corrected_at?: string | null
}

/** Réponse de `GET /evaluations/sessions/{id}/answers/`. */
export interface SessionAnswers {
    count: number
    results: Answer[]
    /** Questions de l'examen restées sans réponse : elles comptent pour 0. */
    unanswered: Question[]
    session_status: SessionStatus
    pending_correction: number
}

// ─── Formations ───────────────────────────────────────────────────────────────

export interface Course {
    id: number
    training: number
    training_detail?: { id: number; title: string } | null
    instructor: number | null
    instructor_name?: string | null
    title: string
    content: string
    order: number
    is_published: boolean
    created_at?: string
}

// ─── Fiche agent ──────────────────────────────────────────────────────────────

export interface AgentSkill {
    id: number
    agent: number
    name: string
    level: number
    acquired_at: string | null
    notes: string
}

export interface AgentCertification {
    id: number
    agent: number
    name: string
    issuing_body: string
    issue_date: string
    expiry_date: string | null
}

export interface PerformanceIndicator {
    id: number
    agent: number
    year: number
    score: string | number
    evaluator: number | null
    comments: string
}

// ─── Audit ────────────────────────────────────────────────────────────────────

export interface LoginHistory {
    id: number
    user: number | null
    matricule_attempted: string
    result: 'SUCCESS' | 'FAILURE'
    ip_address: string | null
    user_agent: string
    timestamp: string
}

/** Rôles fonctionnels, dans l'ordre d'habilitation décroissant. */
export const FUNCTIONAL_ROLES = [
    'ADMIN', 'UNIT_CHIEF', 'APPROVER', 'EVALUATOR',
    'MENTOR', 'INSTRUCTOR',
] as const

export type FunctionalRole = (typeof FUNCTIONAL_ROLES)[number]

export const FunctionalRoleLabels: Record<FunctionalRole, string> = {
    ADMIN: 'Administrateur',
    UNIT_CHIEF: "Chef d'unité",
    APPROVER: 'Approbateur',
    EVALUATOR: 'Évaluateur',
    MENTOR: 'Mentor',
    INSTRUCTOR: 'Instructeur',
}


// ─── Stages et maintien de qualification ──────────────────────────────────────

export interface Internship {
    id: number
    agent: number
    agent_detail?: {
        id: number
        matricule?: string
        full_name?: string
        first_name?: string
        last_name?: string
    } | null
    training: number
    training_detail?: { id: number; title: string } | null
    internship_type?: string
    start_date: string
    end_date: string
    score?: string | number | null
    is_passed?: boolean | null
}

export type MaintenanceStatus = 'PENDING' | 'PASSED' | 'FAILED' | 'WAIVED'

export const MaintenanceStatusLabels: Record<MaintenanceStatus, string> = {
    PENDING: 'En attente',
    PASSED: 'Réussi',
    FAILED: 'Échoué',
    WAIVED: 'Dispensé',
}

export interface QualificationMaintenance {
    id: number
    agent: number
    agent_detail?: {
        id: number
        matricule?: string
        full_name?: string
        first_name?: string
        last_name?: string
    } | null
    training: number
    training_detail?: { id: number; title: string } | null
    maintenance_status: MaintenanceStatus
    due_date: string
    score?: string | number | null
    notes?: string
    evaluated_at?: string | null
}


// ─── Registre d'approbation ───────────────────────────────────────────────────

export type WorkflowStatus = 'DRAFT' | 'SUBMITTED' | 'APPROVED' | 'REJECTED'

export const WorkflowStatusLabels: Record<WorkflowStatus, string> = {
    DRAFT: 'Brouillon',
    SUBMITTED: 'En attente de décision',
    APPROVED: 'Approuvé',
    REJECTED: 'Rejeté',
}

export const WorkflowStatusColors: Record<WorkflowStatus, string> = {
    DRAFT: 'bg-gray-100 text-gray-700',
    SUBMITTED: 'bg-warning-100 text-warning-700',
    APPROVED: 'bg-success-100 text-success-700',
    REJECTED: 'bg-danger-100 text-danger-700',
}

/** Modules raccordés au registre, tels que le backend les nomme. */
export type WorkflowModule = 'report' | 'mentoringrecord' | 'examsession'

/** Objet soumis à décision, joint par le serializer. */
export interface WorkflowTarget {
    id: number
    label: string
    agent: { id: number; matricule: string; full_name: string } | null
    /** Chemin frontend vers l'objet, ou null s'il a été supprimé. */
    route: string | null
    deleted: boolean
}

export interface ApprovalWorkflow {
    id: number
    content_type: number
    object_id: number
    workflow_status: WorkflowStatus
    module: WorkflowModule | string | null
    module_label: string | null
    target: WorkflowTarget | null
    submitted_by: number | null
    submitted_by_name: string | null
    approver: number | null
    approver_name: string | null
    unit_chief: number | null
    unit_chief_name: string | null
    approver_comment: string
    unit_chief_comment: string
    submitted_at: string | null
    approved_at: string | null
    rejected_at: string | null
    created_at: string
}
