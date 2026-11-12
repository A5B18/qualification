/**
 * Détail d'une session d'examen — l'écran qui porte le workflow en 4 étapes.
 *
 * C'était la pièce manquante du projet : `grade-answer` attend un `answer_id`,
 * mais aucun écran n'affichait les réponses d'une session. L'évaluateur ne
 * pouvait donc pas corriger depuis l'interface, et le bouton « Soumettre »
 * partait systématiquement vers un 400 « N réponse(s) non corrigées ».
 *
 * Le même écran sert trois lectures, selon le rôle et l'état de la session :
 *   • ÉVALUATEUR, session SUBMITTED / CORRECTING / REJECTED → saisie des notes
 *   • CHEF D'UNITÉ, session PENDING_APPROVAL                → approuver / rejeter
 *   • AGENT                                                 → relecture de sa copie
 *     (sans le corrigé, que le backend ne lui envoie pas)
 */

import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
    ArrowLeft, CheckCircle2, XCircle, Send, ShieldCheck,
    AlertTriangle, FileText, Clock, User as UserIcon,
} from 'lucide-react'

import { evaluationsApi } from '../../api'
import { apiErrorMessage } from '../../api/client'
import { useAuth } from '../../store/authContextValue'
import {
    SessionStatusLabels, SessionStatusColors,
    QuestionTypeLabels,
    type Answer, type ExamSession, type SessionAnswers,
    type SessionStatus, type QuestionType, type User,
} from '../../types'
import { formatDate } from '../../utils/dates'

// ─── Habilitations ────────────────────────────────────────────────────────────

function hasRole(user: User | null, role: string): boolean {
    return Boolean(user?.is_superuser || user?.is_admin || user?.roles?.includes(role))
}

/** États dans lesquels le backend accepte une correction. */
const GRADABLE: SessionStatus[] = ['SUBMITTED', 'CORRECTING', 'REJECTED']

// ─── Saisie d'une note ────────────────────────────────────────────────────────

type GradePayload = {
    answer_id: number
    is_correct: boolean
    evaluator_score: number
    feedback: string
}

function AnswerCard({
    answer, index, canGrade, onGrade, isSaving,
}: {
    answer: Answer
    index: number
    canGrade: boolean
    onGrade: (payload: GradePayload) => void
    isSaving: boolean
}) {
    const question = answer.question_detail
    const maxPoints = question?.points ?? 0
    const alreadyGraded = answer.evaluator_score !== null

    const [score, setScore] = useState<string>(
        answer.evaluator_score !== null ? String(answer.evaluator_score) : '',
    )
    const [isCorrect, setIsCorrect] = useState<boolean>(answer.is_correct ?? false)
    const [feedback, setFeedback] = useState(answer.feedback ?? '')

    // Le backend borne la note au barème de la question et répond 400 sinon.
    // On prévient la saisie fautive ici pour ne pas faire un aller-retour.
    const numericScore = Number(score)
    const scoreIsValid =
        score.trim() !== '' && Number.isFinite(numericScore)
        && numericScore >= 0 && numericScore <= maxPoints

    const scoreError =
        score.trim() === '' ? null
            : !Number.isFinite(numericScore) ? 'Le score doit être un nombre.'
                : numericScore < 0 || numericScore > maxPoints
                    ? `Le score doit être compris entre 0 et ${maxPoints} (barème de la question).`
                    : null

    return (
        <div className={`card p-5 border-l-4 ${alreadyGraded ? 'border-l-success-500' : 'border-l-warning-400'}`}>
            <div className="flex items-start justify-between gap-4 mb-3">
                <div className="min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-semibold text-gray-400">Question {index + 1}</span>
                        {question?.question_type && (
                            <span className="badge bg-gray-100 text-gray-600">
                                {QuestionTypeLabels[question.question_type as QuestionType] ?? question.question_type}
                            </span>
                        )}
                        <span className="badge bg-asecna-50 text-asecna-700">{maxPoints} pt{maxPoints > 1 ? 's' : ''}</span>
                    </div>
                    <p className="text-sm font-medium text-gray-900">{question?.text ?? '(énoncé indisponible)'}</p>
                </div>
                {alreadyGraded && (
                    <span className="shrink-0 text-sm font-semibold text-success-700">
                        {answer.evaluator_score} / {maxPoints}
                    </span>
                )}
            </div>

            <div className="rounded-lg bg-gray-50 border border-gray-100 p-3 mb-3">
                <p className="text-xs uppercase tracking-wide text-gray-400 mb-1">Réponse de l'agent</p>
                <p className="text-sm text-gray-800 whitespace-pre-wrap">
                    {answer.response || <span className="text-gray-400 italic">Aucune réponse saisie</span>}
                </p>
            </div>

            {/* Le corrigé n'est présent que si le backend nous l'a envoyé,
                c'est-à-dire pour un profil habilité à corriger. */}
            {question?.correct_answer && (
                <div className="rounded-lg bg-success-50 border border-success-100 p-3 mb-3">
                    <p className="text-xs uppercase tracking-wide text-success-600 mb-1">Réponse attendue</p>
                    <p className="text-sm text-success-900 whitespace-pre-wrap">{question.correct_answer}</p>
                </div>
            )}

            {canGrade ? (
                <form
                    className="space-y-3 pt-3 border-t border-gray-100"
                    onSubmit={(e) => {
                        e.preventDefault()
                        if (!scoreIsValid) return
                        onGrade({
                            answer_id: answer.id,
                            is_correct: isCorrect,
                            evaluator_score: numericScore,
                            feedback,
                        })
                    }}
                >
                    <div className="flex flex-wrap items-end gap-3">
                        <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1">
                                Note (0 à {maxPoints})
                            </label>
                            <input
                                type="number" step="0.25" min={0} max={maxPoints}
                                value={score}
                                onChange={(e) => setScore(e.target.value)}
                                className="w-28 px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-asecna-500"
                                placeholder="0"
                            />
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1">Appréciation</label>
                            <div className="flex rounded-lg overflow-hidden border border-gray-200">
                                <button
                                    type="button"
                                    onClick={() => setIsCorrect(true)}
                                    className={`px-3 py-2 text-sm flex items-center gap-1.5 transition-colors ${isCorrect ? 'bg-success-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}
                                >
                                    <CheckCircle2 size={14} /> Correcte
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setIsCorrect(false)}
                                    className={`px-3 py-2 text-sm flex items-center gap-1.5 transition-colors ${!isCorrect ? 'bg-danger-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}
                                >
                                    <XCircle size={14} /> Incorrecte
                                </button>
                            </div>
                        </div>
                        <button
                            type="submit"
                            disabled={!scoreIsValid || isSaving}
                            className="px-4 py-2 rounded-lg text-sm font-medium bg-asecna-600 text-white hover:bg-asecna-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                        >
                            {alreadyGraded ? 'Modifier la note' : 'Enregistrer la note'}
                        </button>
                    </div>

                    {scoreError && (
                        <p className="text-xs text-danger-600 flex items-center gap-1">
                            <AlertTriangle size={12} /> {scoreError}
                        </p>
                    )}

                    <textarea
                        value={feedback}
                        onChange={(e) => setFeedback(e.target.value)}
                        rows={2}
                        placeholder="Commentaire à l'attention de l'agent (facultatif)"
                        className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-asecna-500"
                    />
                </form>
            ) : (
                (answer.feedback || alreadyGraded) && (
                    <div className="pt-3 border-t border-gray-100">
                        {alreadyGraded && (
                            <p className="text-sm">
                                <span className="text-gray-500">Note attribuée : </span>
                                <span className="font-semibold">{answer.evaluator_score} / {maxPoints}</span>
                                {answer.is_correct !== null && (
                                    <span className={`ml-2 badge ${answer.is_correct ? 'bg-success-100 text-success-700' : 'bg-danger-100 text-danger-700'}`}>
                                        {answer.is_correct ? 'Correcte' : 'Incorrecte'}
                                    </span>
                                )}
                            </p>
                        )}
                        {answer.feedback && (
                            <p className="text-sm text-gray-600 mt-1 italic">« {answer.feedback} »</p>
                        )}
                    </div>
                )
            )}
        </div>
    )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function SessionDetailPage() {
    const { id } = useParams<{ id: string }>()
    const sessionId = Number(id)
    const navigate = useNavigate()
    const qc = useQueryClient()
    const { user } = useAuth()

    const [flash, setFlash] = useState<{ text: string; ok: boolean } | null>(null)
    const [rejectOpen, setRejectOpen] = useState(false)
    const [rejectReason, setRejectReason] = useState('')

    const notify = (text: string, ok = true) => {
        setFlash({ text, ok })
        setTimeout(() => setFlash(null), 5000)
    }

    const { data: session, isLoading: loadingSession, isError } = useQuery<ExamSession>({
        queryKey: ['session', sessionId],
        queryFn: () => evaluationsApi.session(sessionId).then(r => r.data),
        enabled: Number.isFinite(sessionId),
    })

    const { data: copie, isLoading: loadingAnswers } = useQuery<SessionAnswers>({
        queryKey: ['session-answers', sessionId],
        queryFn: () => evaluationsApi.sessionAnswers(sessionId).then(r => r.data),
        enabled: Number.isFinite(sessionId),
    })

    const refresh = () => {
        qc.invalidateQueries({ queryKey: ['session', sessionId] })
        qc.invalidateQueries({ queryKey: ['session-answers', sessionId] })
        qc.invalidateQueries({ queryKey: ['sessions'] })
    }

    const gradeMut = useMutation({
        mutationFn: (payload: GradePayload) => evaluationsApi.gradeAnswer(sessionId, payload),
        onSuccess: () => { refresh(); notify('Note enregistrée.') },
        onError: (err) => notify(apiErrorMessage(err, "La note n'a pas pu être enregistrée."), false),
    })

    const submitMut = useMutation({
        mutationFn: () => evaluationsApi.submitForApproval(sessionId),
        onSuccess: (res) => {
            refresh()
            notify(`Correction soumise au chef d'unité — score calculé : ${res.data.score}/100`)
        },
        onError: (err) => notify(apiErrorMessage(err, 'Soumission impossible.'), false),
    })

    const approveMut = useMutation({
        mutationFn: () => evaluationsApi.approveSession(sessionId),
        onSuccess: () => { refresh(); notify('Correction approuvée — le score est officiel.') },
        onError: (err) => notify(apiErrorMessage(err, 'Approbation impossible.'), false),
    })

    const rejectMut = useMutation({
        mutationFn: (reason: string) => evaluationsApi.rejectSession(sessionId, { reason }),
        onSuccess: () => {
            refresh(); setRejectOpen(false); setRejectReason('')
            notify("Correction rejetée — l'évaluateur doit la reprendre.")
        },
        onError: (err) => notify(apiErrorMessage(err, 'Rejet impossible.'), false),
    })

    if (loadingSession || loadingAnswers) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-asecna-600" />
            </div>
        )
    }

    if (isError || !session) {
        return (
            <div className="card text-center py-12">
                <AlertTriangle size={36} className="mx-auto text-gray-300 mb-3" />
                <p className="text-gray-600">Session introuvable, ou vous n'y avez pas accès.</p>
                <Link to="/evaluations" className="text-asecna-600 text-sm mt-3 inline-block">
                    Retour aux évaluations
                </Link>
            </div>
        )
    }

    const status = session.session_status
    const answers = copie?.results ?? []
    const unanswered = copie?.unanswered ?? []
    const pending = copie?.pending_correction ?? 0

    const isEvaluator = hasRole(user, 'EVALUATOR')
    const isChief = hasRole(user, 'UNIT_CHIEF') || hasRole(user, 'APPROVER')

    const canGrade = isEvaluator && GRADABLE.includes(status)
    // Le backend n'accepte la soumission que depuis CORRECTING ou REJECTED,
    // et seulement si plus aucune réponse n'attend de note.
    const canSubmit = isEvaluator && (status === 'CORRECTING' || status === 'REJECTED') && pending === 0
    const canDecide = isChief && status === 'PENDING_APPROVAL'

    const maxTotal = [...answers.map(a => a.question_detail?.points ?? 0),
    ...unanswered.map(q => q.points)].reduce((a, b) => a + b, 0)
    const earned = answers.reduce((acc, a) => acc + Number(a.evaluator_score ?? 0), 0)

    return (
        <div className="space-y-5">
            {/* En-tête */}
            <div className="flex items-start justify-between gap-4 flex-wrap">
                <div>
                    <button
                        onClick={() => navigate('/evaluations')}
                        className="text-sm text-gray-500 hover:text-gray-800 flex items-center gap-1 mb-2"
                    >
                        <ArrowLeft size={15} /> Évaluations
                    </button>
                    <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                        <FileText size={22} className="text-asecna-600" />
                        {session.exam_detail?.title ?? `Examen #${session.exam}`}
                    </h1>
                    <p className="text-sm text-gray-500 mt-1 flex items-center gap-3 flex-wrap">
                        <span className="flex items-center gap-1">
                            <UserIcon size={13} />
                            {session.agent_detail
                                ? `${session.agent_detail.first_name} ${session.agent_detail.last_name} (${session.agent_detail.matricule})`
                                : `Agent #${session.agent}`}
                        </span>
                        {session.submitted_at && (
                            <span className="flex items-center gap-1">
                                <Clock size={13} /> Copie rendue le {formatDate(session.submitted_at)}
                            </span>
                        )}
                    </p>
                </div>
                <span className={`badge ${SessionStatusColors[status]} text-sm px-3 py-1`}>
                    {SessionStatusLabels[status]}
                </span>
            </div>

            {flash && (
                <div className={`rounded-lg px-4 py-3 text-sm ${flash.ok ? 'bg-success-50 text-success-800 border border-success-200' : 'bg-danger-50 text-danger-800 border border-danger-200'}`}>
                    {flash.text}
                </div>
            )}

            {status === 'REJECTED' && session.rejection_reason && (
                <div className="rounded-lg px-4 py-3 bg-danger-50 border border-danger-200 text-sm text-danger-800">
                    <span className="font-semibold">Motif du rejet par le chef d'unité : </span>
                    {session.rejection_reason}
                </div>
            )}

            {/* Avancement de la correction */}
            <div className="card p-4">
                <div className="flex flex-wrap items-center justify-between gap-4">
                    <div className="flex items-center gap-6 text-sm">
                        <div>
                            <p className="text-gray-400 text-xs uppercase tracking-wide">Réponses corrigées</p>
                            <p className="font-semibold text-gray-900">
                                {answers.length - pending} / {answers.length}
                            </p>
                        </div>
                        <div>
                            <p className="text-gray-400 text-xs uppercase tracking-wide">Points attribués</p>
                            <p className="font-semibold text-gray-900">{earned} / {maxTotal}</p>
                        </div>
                        <div>
                            <p className="text-gray-400 text-xs uppercase tracking-wide">
                                {status === 'GRADED' ? 'Score officiel' : 'Score provisoire'}
                            </p>
                            <p className="font-semibold text-gray-900">
                                {session.score !== null ? `${session.score} / 100` : '—'}
                                {session.is_passed !== null && (
                                    <span className={`ml-2 badge ${session.is_passed ? 'bg-success-100 text-success-700' : 'bg-danger-100 text-danger-700'}`}>
                                        {session.is_passed ? 'Admis' : 'Non admis'}
                                    </span>
                                )}
                            </p>
                        </div>
                    </div>

                    <div className="flex items-center gap-2">
                        {isEvaluator && (status === 'CORRECTING' || status === 'REJECTED') && (
                            <button
                                onClick={() => submitMut.mutate()}
                                disabled={!canSubmit || submitMut.isPending}
                                title={pending > 0
                                    ? `${pending} réponse(s) restent à corriger`
                                    : "Soumettre la correction au chef d'unité"}
                                className="px-4 py-2 rounded-lg text-sm font-medium bg-accent-600 text-white hover:bg-accent-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center gap-1.5"
                            >
                                <Send size={15} /> Soumettre au chef d'unité
                            </button>
                        )}
                        {canDecide && (
                            <>
                                <button
                                    onClick={() => approveMut.mutate()}
                                    disabled={approveMut.isPending}
                                    className="px-4 py-2 rounded-lg text-sm font-medium bg-success-600 text-white hover:bg-success-700 disabled:opacity-40 transition-colors flex items-center gap-1.5"
                                >
                                    <ShieldCheck size={15} /> Approuver
                                </button>
                                <button
                                    onClick={() => setRejectOpen(true)}
                                    className="px-4 py-2 rounded-lg text-sm font-medium bg-white border border-danger-200 text-danger-700 hover:bg-danger-50 transition-colors"
                                >
                                    Rejeter
                                </button>
                            </>
                        )}
                    </div>
                </div>

                {isEvaluator && pending > 0 && (status === 'CORRECTING' || status === 'REJECTED') && (
                    <p className="text-xs text-warning-700 mt-3 flex items-center gap-1">
                        <AlertTriangle size={12} />
                        {pending} réponse(s) n'ont pas encore été corrigées — la soumission restera
                        refusée tant qu'il en reste.
                    </p>
                )}
            </div>

            {/* Formulaire de rejet */}
            {rejectOpen && (
                <div className="card p-5 border border-danger-200">
                    <h3 className="font-semibold text-gray-900 mb-2">Motif du rejet</h3>
                    <p className="text-sm text-gray-500 mb-3">
                        Le motif est obligatoire : il est transmis à l'évaluateur, qui pourra
                        reprendre sa correction.
                    </p>
                    <textarea
                        value={rejectReason}
                        onChange={(e) => setRejectReason(e.target.value)}
                        rows={3}
                        className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-danger-400"
                        placeholder="Expliquer pourquoi la correction est rejetée…"
                    />
                    <div className="flex gap-2 mt-3">
                        <button
                            onClick={() => rejectMut.mutate(rejectReason)}
                            disabled={!rejectReason.trim() || rejectMut.isPending}
                            className="px-4 py-2 rounded-lg text-sm font-medium bg-danger-600 text-white hover:bg-danger-700 disabled:opacity-40"
                        >
                            Confirmer le rejet
                        </button>
                        <button
                            onClick={() => { setRejectOpen(false); setRejectReason('') }}
                            className="px-4 py-2 rounded-lg text-sm text-gray-600 hover:bg-gray-50"
                        >
                            Annuler
                        </button>
                    </div>
                </div>
            )}

            {/* Copie */}
            <div className="space-y-3">
                <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
                    Copie de l'agent ({answers.length} réponse{answers.length > 1 ? 's' : ''})
                </h2>

                {answers.length === 0 ? (
                    <div className="card text-center py-10 text-gray-400">
                        <FileText size={34} className="mx-auto mb-2 opacity-30" />
                        <p>Aucune réponse n'a été soumise pour cette session.</p>
                    </div>
                ) : (
                    answers.map((answer, i) => (
                        <AnswerCard
                            // Le `key` intègre la correction : il force le remontage
                            // du formulaire après enregistrement, pour que les champs
                            // reflètent la note réellement retenue par le serveur.
                            key={`${answer.id}-${answer.evaluator_score ?? 'vide'}`}
                            answer={answer}
                            index={i}
                            canGrade={canGrade}
                            isSaving={gradeMut.isPending}
                            onGrade={(payload) => gradeMut.mutate(payload)}
                        />
                    ))
                )}

                {/* Les questions sans réponse comptent pour 0 dans le score : les
                    masquer laisserait croire que la copie est complète. */}
                {unanswered.length > 0 && (
                    <div className="card p-4 bg-gray-50 border-dashed">
                        <h3 className="text-sm font-semibold text-gray-600 mb-2">
                            {unanswered.length} question(s) laissée(s) sans réponse
                        </h3>
                        <p className="text-xs text-gray-500 mb-3">
                            Elles comptent pour 0 dans le score : le barème retenu est celui de
                            l'examen complet, pas celui des seules questions traitées.
                        </p>
                        <ul className="space-y-1.5">
                            {unanswered.map(q => (
                                <li key={q.id} className="text-sm text-gray-700 flex items-start gap-2">
                                    <span className="badge bg-gray-200 text-gray-600 shrink-0">{q.points} pt</span>
                                    <span>{q.text}</span>
                                </li>
                            ))}
                        </ul>
                    </div>
                )}
            </div>
        </div>
    )
}
