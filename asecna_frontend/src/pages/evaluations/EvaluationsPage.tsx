import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { evaluationsApi, trainingApi } from '../../api'
import { useAuth } from '../../store/authContextValue'
import {
    Award, AlertTriangle,
    ThumbsUp, ThumbsDown, Plus, X, ChevronRight, PenLine,
} from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { apiErrorMessage } from '../../api/client'
import type { User, ExamSession, Exam, Training } from '../../types'

const SESSION_STATUS_LABELS: Record<string, string> = {
    IN_PROGRESS: 'En cours',
    SUBMITTED: 'Soumise',
    CORRECTING: 'En correction',
    PENDING_APPROVAL: 'En attente chef',
    GRADED: 'Validée ✓',
    REJECTED: 'Rejetée',
}
const SESSION_STATUS_COLORS: Record<string, string> = {
    IN_PROGRESS: 'bg-blue-100 text-blue-700',
    SUBMITTED: 'bg-yellow-100 text-yellow-700',
    CORRECTING: 'bg-orange-100 text-orange-700',
    PENDING_APPROVAL: 'bg-purple-100 text-purple-700',
    GRADED: 'bg-green-100 text-green-700',
    REJECTED: 'bg-red-100 text-red-700',
}

function canCreateExam(user: User | null): boolean {
    const roles: string[] = user?.roles ?? []
    return user?.is_superuser || user?.is_admin ||
        roles.includes('ADMIN') || roles.includes('EVALUATOR') || roles.includes('INSTRUCTOR')
}

function canApprove(user: User | null): boolean {
    const roles: string[] = user?.roles ?? []
    return user?.is_superuser || user?.is_admin ||
        roles.includes('ADMIN') || roles.includes('UNIT_CHIEF') || roles.includes('APPROVER')
}

export default function EvaluationsPage() {
    const { user } = useAuth()
    const qc = useQueryClient()
    const navigate = useNavigate()

    // États
    const [showCreateExam, setShowCreateExam] = useState(false)
    const [rejectSessionId, setRejectSessionId] = useState<number | null>(null)
    const [rejectReason, setRejectReason] = useState('')
    const [actionMsg, setActionMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null)

    // Formulaire création examen
    const [examForm, setExamForm] = useState({
        title: '', description: '', passing_score: 70, training: '',
    })

    const flash = (text: string, type: 'success' | 'error' = 'success') => {
        setActionMsg({ text, type })
        setTimeout(() => setActionMsg(null), 4000)
    }

    // ── Queries ──────────────────────────────────────────────────────────────
    const { data: examsData, isLoading: loadingExams } = useQuery({
        queryKey: ['exams'],
        queryFn: () => evaluationsApi.exams().then(r => r.data),
    })
    const { data: sessionsData, isLoading: loadingSessions } = useQuery({
        queryKey: ['sessions'],
        queryFn: () => evaluationsApi.sessions().then(r => r.data),
    })
    const { data: trainingsData } = useQuery({
        queryKey: ['trainings-select'],
        queryFn: () => trainingApi.trainings().then(r => r.data),
        enabled: showCreateExam,
    })

    const exams = examsData?.results ?? []
    const sessions = sessionsData?.results ?? []
    const trainings = trainingsData?.results ?? []

    const pendingApproval = sessions.filter((s: ExamSession) => s.session_status === 'PENDING_APPROVAL')
    const graded = sessions.filter((s: ExamSession) => s.session_status === 'GRADED')
    const avgScore = graded.length > 0
        ? Math.round(graded.reduce((acc: number, s: ExamSession) => acc + Number(s.score ?? 0), 0) / graded.length)
        : 0

    // ── Mutations ─────────────────────────────────────────────────────────────

    const approveMut = useMutation({
        mutationFn: (id: number) => evaluationsApi.approveSession(id),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['sessions'] })
            flash('✅ Session approuvée')
        },
    })

    const rejectMut = useMutation({
        mutationFn: ({ id, reason }: { id: number; reason: string }) =>
            evaluationsApi.rejectSession(id, { reason }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['sessions'] })
            setRejectSessionId(null)
            setRejectReason('')
            flash('Session rejetée — l\'évaluateur doit recorriger')
        },
    })

    const submitApprovalMut = useMutation({
        mutationFn: (id: number) => evaluationsApi.submitForApproval(id),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['sessions'] })
            flash('📤 Correction soumise au chef d\'unité')
        },
    })

    const handleCreateExam = async (e: React.FormEvent) => {
        e.preventDefault()
        try {
            await evaluationsApi.create({
                title: examForm.title,
                description: examForm.description,
                passing_score: Number(examForm.passing_score),
                training: examForm.training ? Number(examForm.training) : null,
            })
            qc.invalidateQueries({ queryKey: ['exams'] })
            setShowCreateExam(false)
            setExamForm({ title: '', description: '', passing_score: 70, training: '' })
            flash('✅ Examen créé avec succès')
        } catch (err: unknown) {
            flash(apiErrorMessage(err, '❌ Erreur lors de la création'), 'error')
        }
    }

    return (
        <div className="space-y-6">
            {/* En-tête */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                        <Award size={24} className="text-asecna-600" /> Évaluations
                    </h1>
                    <p className="text-gray-400 text-sm mt-0.5">
                        {examsData?.count ?? 0} examens · {sessionsData?.count ?? 0} sessions
                    </p>
                </div>
                {canCreateExam(user) && (
                    <button
                        onClick={() => setShowCreateExam(true)}
                        className="flex items-center gap-2 px-4 py-2 bg-asecna-600 hover:bg-asecna-700 text-white rounded-xl text-sm font-medium transition-colors shadow-sm"
                    >
                        <Plus size={16} /> Créer un examen
                    </button>
                )}
            </div>

            {/* Notification */}
            {actionMsg && (
                <div className={`p-3 rounded-xl text-sm font-medium border ${actionMsg.type === 'success'
                        ? 'bg-green-50 border-green-200 text-green-800'
                        : 'bg-red-50 border-red-200 text-red-800'
                    }`}>
                    {actionMsg.text}
                </div>
            )}

            {/* KPIs */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {[
                    { label: 'Examens', value: examsData?.count ?? 0, color: 'bg-asecna-50 border-asecna-200 text-asecna-700' },
                    { label: 'Sessions', value: sessionsData?.count ?? 0, color: 'bg-blue-50 border-blue-200 text-blue-700' },
                    { label: 'En attente approbation', value: pendingApproval.length, color: pendingApproval.length > 0 ? 'bg-purple-50 border-purple-300 text-purple-700' : 'bg-gray-50 border-gray-200 text-gray-500' },
                    { label: 'Score moyen validé', value: graded.length > 0 ? `${avgScore}%` : '—', color: avgScore >= 70 ? 'bg-green-50 border-green-200 text-green-700' : 'bg-gray-50 border-gray-200 text-gray-500' },
                ].map(({ label, value, color }) => (
                    <div key={label} className={`rounded-xl border p-5 ${color}`}>
                        <div className="text-2xl font-bold">{value}</div>
                        <div className="text-sm mt-1">{label}</div>
                    </div>
                ))}
            </div>

            {/* Corrections en attente (chef d'unité / approbateur) */}
            {canApprove(user) && pendingApproval.length > 0 && (
                <div className="card border-l-4 border-purple-500">
                    <h2 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                        <AlertTriangle size={18} className="text-purple-600" />
                        Corrections à valider ({pendingApproval.length})
                    </h2>
                    <div className="space-y-3">
                        {pendingApproval.map((session: ExamSession) => (
                            <div key={session.id} className="flex items-center justify-between p-3 rounded-xl bg-purple-50 border border-purple-100">
                                <div>
                                    <div className="text-sm font-medium text-gray-900">
                                        {session.agent_detail?.first_name} {session.agent_detail?.last_name}
                                        <span className="ml-2 text-xs text-gray-500">({session.agent_detail?.matricule})</span>
                                    </div>
                                    <div className="text-xs text-gray-500 mt-0.5">
                                        {session.exam_detail?.title} — Score provisoire :
                                        <strong className={`ml-1 ${Number(session.score ?? 0) >= (session.exam_detail?.passing_score ?? 70) ? 'text-green-600' : 'text-red-600'}`}>
                                            {session.score ?? '?'}/100
                                        </strong>
                                    </div>
                                    {session.graded_by_detail && (
                                        <div className="text-xs text-purple-600 mt-0.5">
                                            Corrigé par : {session.graded_by_detail?.first_name} {session.graded_by_detail?.last_name}
                                        </div>
                                    )}
                                </div>
                                <div className="flex items-center gap-2">
                                    <button
                                        onClick={() => approveMut.mutate(session.id)}
                                        disabled={approveMut.isPending}
                                        className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-white bg-green-600 hover:bg-green-700 rounded-lg transition-colors"
                                    >
                                        <ThumbsUp size={12} /> Approuver
                                    </button>
                                    <button
                                        onClick={() => { setRejectSessionId(session.id); setRejectReason('') }}
                                        className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-white bg-red-500 hover:bg-red-600 rounded-lg transition-colors"
                                    >
                                        <ThumbsDown size={12} /> Rejeter
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                {/* Examens */}
                <div className="card">
                    <h2 className="font-semibold text-gray-900 mb-4">Examens disponibles</h2>
                    {loadingExams ? (
                        <div className="flex items-center justify-center h-24">
                            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-asecna-600" />
                        </div>
                    ) : exams.length === 0 ? (
                        <div className="text-center py-10 text-gray-400">
                            <Award size={36} className="mx-auto mb-2 opacity-30" />
                            <p className="text-sm">Aucun examen créé</p>
                            {canCreateExam(user) && (
                                <button
                                    onClick={() => setShowCreateExam(true)}
                                    className="mt-3 text-sm text-asecna-600 hover:underline"
                                >
                                    Créer le premier examen →
                                </button>
                            )}
                        </div>
                    ) : (
                        <div className="space-y-2">
                            {exams.map((exam: Exam) => (
                                <div key={exam.id} className="flex items-center justify-between gap-2 p-3 rounded-xl bg-gray-50 hover:bg-gray-100 transition-colors">
                                    <div className="min-w-0">
                                        <div className="text-sm font-medium text-gray-900">{exam.title}</div>
                                        <div className="text-xs text-gray-500">
                                            {exam.training_detail?.title ?? 'Sans formation'} · Seuil {exam.passing_score ?? 70}%
                                            {exam.questions_count !== undefined && ` · ${exam.questions_count} question${exam.questions_count > 1 ? 's' : ''}`}
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2 shrink-0">
                                        <span className={`badge text-xs ${exam.exam_status === 'PUBLISHED' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                                            {exam.exam_status === 'PUBLISHED' ? 'Publié' : 'Brouillon'}
                                        </span>
                                        {/* Un évaluateur compose l'examen ; un agent le passe. */}
                                        {canCreateExam(user) ? (
                                            <Link
                                                to={`/evaluations/exams/${exam.id}`}
                                                title="Composer l'examen (questions, publication)"
                                                className="text-xs px-2 py-1 bg-asecna-50 text-asecna-700 hover:bg-asecna-100 rounded-lg transition-colors flex items-center gap-1"
                                            >
                                                <PenLine size={12} /> Composer
                                            </Link>
                                        ) : exam.exam_status === 'PUBLISHED' && (
                                            <Link
                                                to={`/evaluations/exams/${exam.id}/compose`}
                                                className="text-xs px-2 py-1 bg-asecna-600 text-white hover:bg-asecna-700 rounded-lg transition-colors"
                                            >
                                                Passer l'épreuve
                                            </Link>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Sessions */}
                <div className="card">
                    <h2 className="font-semibold text-gray-900 mb-4">Suivi des sessions</h2>
                    {loadingSessions ? (
                        <div className="flex items-center justify-center h-24">
                            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-asecna-600" />
                        </div>
                    ) : sessions.length === 0 ? (
                        <p className="text-gray-400 text-sm text-center py-10">Aucune session enregistrée</p>
                    ) : (
                        <div className="space-y-2">
                            {sessions.slice(0, 10).map((session: ExamSession) => {
                                const st = session.session_status as string
                                const pending = session.pending_correction_count ?? 0
                                // La soumission n'est acceptée que depuis CORRECTING ou
                                // REJECTED, et seulement si tout est corrigé. L'ancien
                                // bouton ignorait le second point : il partait donc vers
                                // un 400 « N réponse(s) non corrigées ». La ligne mène
                                // désormais à l'écran de correction, qui permet justement
                                // de les corriger.
                                const canSubmit =
                                    (st === 'CORRECTING' || st === 'REJECTED') && pending === 0
                                return (
                                    <div
                                        key={session.id}
                                        onClick={() => navigate(`/evaluations/sessions/${session.id}`)}
                                        className="flex items-center justify-between gap-2 p-3 rounded-xl bg-gray-50 hover:bg-gray-100 cursor-pointer transition-colors"
                                    >
                                        <div className="min-w-0">
                                            <div className="text-sm font-medium text-gray-900">
                                                {session.agent_detail?.matricule ?? `Agent #${session.agent}`}
                                            </div>
                                            <div className="text-xs text-gray-500">
                                                {session.exam_detail?.title ?? '—'}
                                                {session.score != null &&
                                                    <span className={`ml-2 font-semibold ${Number(session.score) >= (session.exam_detail?.passing_score ?? 70) ? 'text-green-600' : 'text-red-500'}`}>
                                                        {session.score}/100
                                                    </span>
                                                }
                                                {pending > 0 && (
                                                    <span className="ml-2 text-amber-600">
                                                        {pending} réponse(s) à corriger
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-2 shrink-0">
                                            {canSubmit && canCreateExam(user) && (
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation()
                                                        submitApprovalMut.mutate(session.id)
                                                    }}
                                                    disabled={submitApprovalMut.isPending}
                                                    className="text-xs px-2 py-1 bg-purple-100 text-purple-700 hover:bg-purple-200 rounded-lg transition-colors"
                                                >
                                                    Soumettre
                                                </button>
                                            )}
                                            <span className={`badge text-xs ${SESSION_STATUS_COLORS[st] ?? 'bg-gray-100 text-gray-600'}`}>
                                                {SESSION_STATUS_LABELS[st] ?? st}
                                            </span>
                                            <ChevronRight size={15} className="text-gray-300" />
                                        </div>
                                    </div>
                                )
                            })}
                        </div>
                    )}
                </div>
            </div>

            {/* ── Modal : Créer un examen ─────────────────────────────────────────── */}
            {showCreateExam && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
                    <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-md">
                        <div className="flex items-center justify-between mb-5">
                            <h3 className="text-lg font-bold text-gray-900">Créer un examen</h3>
                            <button onClick={() => setShowCreateExam(false)} className="p-1 rounded-lg hover:bg-gray-100">
                                <X size={18} className="text-gray-400" />
                            </button>
                        </div>
                        <form onSubmit={handleCreateExam} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Titre *</label>
                                <input
                                    type="text" required
                                    className="w-full border border-gray-200 rounded-xl p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-asecna-500"
                                    placeholder="Ex: QCM CNS/ATM — Niveau 1"
                                    value={examForm.title}
                                    onChange={e => setExamForm(f => ({ ...f, title: e.target.value }))}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Formation associée</label>
                                <select
                                    className="w-full border border-gray-200 rounded-xl p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-asecna-500"
                                    value={examForm.training}
                                    onChange={e => setExamForm(f => ({ ...f, training: e.target.value }))}
                                >
                                    <option value="">— Aucune formation —</option>
                                    {trainings.map((t: Training) => (
                                        <option key={t.id} value={t.id}>{t.title}</option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Score minimal de réussite (%)</label>
                                <input
                                    type="number" min="0" max="100"
                                    className="w-full border border-gray-200 rounded-xl p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-asecna-500"
                                    value={examForm.passing_score}
                                    onChange={e => setExamForm(f => ({ ...f, passing_score: Number(e.target.value) }))}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                                <textarea
                                    className="w-full border border-gray-200 rounded-xl p-2.5 text-sm min-h-[80px] focus:outline-none focus:ring-2 focus:ring-asecna-500 resize-none"
                                    placeholder="Description de l'examen..."
                                    value={examForm.description}
                                    onChange={e => setExamForm(f => ({ ...f, description: e.target.value }))}
                                />
                            </div>
                            <div className="flex gap-3 justify-end pt-2">
                                <button
                                    type="button"
                                    onClick={() => setShowCreateExam(false)}
                                    className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-xl"
                                >
                                    Annuler
                                </button>
                                <button
                                    type="submit"
                                    className="px-4 py-2 text-sm font-medium text-white bg-asecna-600 hover:bg-asecna-700 rounded-xl transition-colors"
                                >
                                    Créer l'examen
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* ── Modal : Rejeter ────────────────────────────────────────────────── */}
            {rejectSessionId !== null && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
                    <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-md">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-bold text-gray-900">Motif de rejet</h3>
                            <button onClick={() => setRejectSessionId(null)} className="p-1 rounded-lg hover:bg-gray-100">
                                <X size={18} className="text-gray-400" />
                            </button>
                        </div>
                        <textarea
                            className="w-full border border-gray-200 rounded-xl p-3 text-sm focus:outline-none focus:ring-2 focus:ring-red-500 min-h-[100px] resize-none"
                            placeholder="Expliquer pourquoi la correction est rejetée..."
                            value={rejectReason}
                            onChange={e => setRejectReason(e.target.value)}
                        />
                        <div className="flex gap-3 mt-4 justify-end">
                            <button
                                onClick={() => setRejectSessionId(null)}
                                className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-xl"
                            >
                                Annuler
                            </button>
                            <button
                                onClick={() => rejectSessionId && rejectMut.mutate({ id: rejectSessionId, reason: rejectReason })}
                                disabled={!rejectReason.trim() || rejectMut.isPending}
                                className="px-4 py-2 text-sm text-white bg-red-600 hover:bg-red-700 rounded-xl disabled:opacity-40"
                            >
                                Confirmer le rejet
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
