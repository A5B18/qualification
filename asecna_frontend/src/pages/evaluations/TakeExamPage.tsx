/**
 * Composition d'un examen par l'agent.
 *
 * Les trois endpoints de ce parcours (`start-session`, `submit-answer`,
 * `finalize`) existaient côté serveur mais aucun écran ne les appelait :
 * l'agent ne pouvait pas passer une épreuve depuis l'application.
 *
 * Le brouillon vit côté serveur, pas dans le navigateur : chaque réponse est
 * envoyée dès qu'elle est validée (`update_or_create` côté backend), si bien
 * qu'une session interrompue se reprend telle quelle.
 */

import { useEffect, useMemo, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
    ArrowLeft, Send, CheckCircle2, AlertTriangle, Clock, Save,
} from 'lucide-react'

import { evaluationsApi } from '../../api'
import { apiErrorMessage } from '../../api/client'
import {
    QuestionKindLabels,
    type Question, type ExamSession, type SessionAnswers, type Exam,
} from '../../types'

export default function TakeExamPage() {
    const { id } = useParams<{ id: string }>()
    const examId = Number(id)
    const navigate = useNavigate()
    const qc = useQueryClient()

    const [sessionId, setSessionId] = useState<number | null>(null)
    const [draft, setDraft] = useState<Record<number, string>>({})
    const [flash, setFlash] = useState<{ text: string; ok: boolean } | null>(null)
    const [confirmFinalize, setConfirmFinalize] = useState(false)

    const notify = (text: string, ok = true) => {
        setFlash({ text, ok })
        setTimeout(() => setFlash(null), 5000)
    }

    const { data: exam } = useQuery<Exam>({
        queryKey: ['exam', examId],
        queryFn: () => evaluationsApi.exam(examId).then(r => r.data),
        enabled: Number.isFinite(examId),
    })

    const { data: questionsData, isLoading: loadingQuestions } = useQuery<{ results: Question[] }>({
        queryKey: ['exam-questions', examId],
        queryFn: () => evaluationsApi.examQuestions(examId).then(r => r.data),
        enabled: Number.isFinite(examId),
    })

    // Démarrage (ou reprise) de la session : l'endpoint est idempotent
    // (`get_or_create`), un rechargement de page ne crée donc pas de doublon.
    const startMut = useMutation({
        mutationFn: () => evaluationsApi.startSession(examId),
        onSuccess: (res) => setSessionId((res.data as ExamSession).id),
        onError: (err) => notify(apiErrorMessage(err, "L'épreuve n'a pas pu être démarrée."), false),
    })

    useEffect(() => {
        if (Number.isFinite(examId) && sessionId === null && !startMut.isPending) {
            startMut.mutate()
        }
        // Un seul démarrage par examen : les autres dépendances sont stables.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [examId])

    const { data: copie } = useQuery<SessionAnswers>({
        queryKey: ['session-answers', sessionId],
        queryFn: () => evaluationsApi.sessionAnswers(sessionId as number).then(r => r.data),
        enabled: sessionId !== null,
    })

    const { data: session } = useQuery<ExamSession>({
        queryKey: ['session', sessionId],
        queryFn: () => evaluationsApi.session(sessionId as number).then(r => r.data),
        enabled: sessionId !== null,
    })

    // Réponses déjà enregistrées côté serveur, indexées par question
    const saved = useMemo(() => {
        const map: Record<number, string> = {}
        for (const a of copie?.results ?? []) map[a.question] = a.response
        return map
    }, [copie])

    const answerMut = useMutation({
        mutationFn: (payload: { question: number; response: string }) =>
            evaluationsApi.submitAnswer(sessionId as number, payload),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['session-answers', sessionId] })
            notify('Réponse enregistrée.')
        },
        onError: (err) => notify(apiErrorMessage(err, "La réponse n'a pas pu être enregistrée."), false),
    })

    const finalizeMut = useMutation({
        mutationFn: () => evaluationsApi.finalizeSession(sessionId as number),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['sessions'] })
            notify('Copie rendue — elle part en correction.')
            setTimeout(() => navigate('/evaluations'), 1200)
        },
        onError: (err) => notify(apiErrorMessage(err, 'La copie n\'a pas pu être rendue.'), false),
    })

    const questions = questionsData?.results ?? []
    const answeredCount = questions.filter(q => saved[q.id] !== undefined).length
    const status = session?.session_status

    if (loadingQuestions || startMut.isPending) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-asecna-600" />
            </div>
        )
    }

    // Une session déjà rendue ne se recompose pas : le backend refuserait
    // chaque `submit-answer` avec « La session n'est plus en cours ».
    if (status && status !== 'IN_PROGRESS') {
        return (
            <div className="card text-center py-12">
                <CheckCircle2 size={36} className="mx-auto text-success-500 mb-3" />
                <p className="text-gray-700 font-medium">Votre copie a déjà été rendue.</p>
                <p className="text-sm text-gray-500 mt-1">
                    Elle suit son cours : correction par un évaluateur, puis validation du
                    chef d'unité.
                </p>
                <Link
                    to={`/evaluations/sessions/${sessionId}`}
                    className="text-asecna-600 text-sm mt-4 inline-block"
                >
                    Consulter ma copie
                </Link>
            </div>
        )
    }

    return (
        <div className="space-y-5">
            <div>
                <button
                    onClick={() => navigate('/evaluations')}
                    className="text-sm text-gray-500 hover:text-gray-800 flex items-center gap-1 mb-2"
                >
                    <ArrowLeft size={15} /> Évaluations
                </button>
                <h1 className="text-2xl font-bold text-gray-900">{exam?.title ?? 'Épreuve'}</h1>
                <p className="text-sm text-gray-500 mt-1 flex items-center gap-3 flex-wrap">
                    {exam?.duration_minutes && (
                        <span className="flex items-center gap-1">
                            <Clock size={13} /> Durée prévue : {exam.duration_minutes} min
                        </span>
                    )}
                    <span>Seuil de réussite : {exam?.passing_score ?? 70}/100</span>
                </p>
            </div>

            {flash && (
                <div className={`rounded-lg px-4 py-3 text-sm ${flash.ok ? 'bg-success-50 text-success-800 border border-success-200' : 'bg-danger-50 text-danger-800 border border-danger-200'}`}>
                    {flash.text}
                </div>
            )}

            <div className="card p-4 flex flex-wrap items-center justify-between gap-3">
                <div className="text-sm">
                    <span className="text-gray-500">Questions traitées : </span>
                    <span className="font-semibold">{answeredCount} / {questions.length}</span>
                    {answeredCount < questions.length && (
                        <span className="text-gray-400 ml-2">
                            — les questions laissées vides comptent pour 0.
                        </span>
                    )}
                </div>
                <button
                    onClick={() => setConfirmFinalize(true)}
                    disabled={finalizeMut.isPending || sessionId === null}
                    className="px-4 py-2 rounded-lg text-sm font-medium bg-asecna-600 text-white hover:bg-asecna-700 disabled:opacity-40 flex items-center gap-1.5"
                >
                    <Send size={15} /> Rendre ma copie
                </button>
            </div>

            {confirmFinalize && (
                <div className="card p-5 border border-warning-200 bg-warning-50">
                    <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                        <AlertTriangle size={16} className="text-warning-600" /> Rendre la copie ?
                    </h3>
                    <p className="text-sm text-gray-700 mt-1">
                        Une fois rendue, la copie part en correction et ne peut plus être
                        modifiée.
                        {answeredCount < questions.length && (
                            <> Il reste <strong>{questions.length - answeredCount}</strong> question(s)
                                sans réponse ; elles seront notées 0.</>
                        )}
                    </p>
                    <div className="flex gap-2 mt-3">
                        <button
                            onClick={() => finalizeMut.mutate()}
                            disabled={finalizeMut.isPending}
                            className="px-4 py-2 rounded-lg text-sm font-medium bg-asecna-600 text-white hover:bg-asecna-700 disabled:opacity-40"
                        >
                            Confirmer
                        </button>
                        <button
                            onClick={() => setConfirmFinalize(false)}
                            className="px-4 py-2 rounded-lg text-sm text-gray-600 hover:bg-white"
                        >
                            Continuer à composer
                        </button>
                    </div>
                </div>
            )}

            {questions.length === 0 ? (
                <div className="card text-center py-10 text-gray-400">
                    <p>Cet examen ne comporte aucune question.</p>
                </div>
            ) : (
                questions.map((q, i) => {
                    const current = draft[q.id] ?? saved[q.id] ?? ''
                    const isSaved = saved[q.id] !== undefined && saved[q.id] === current
                    return (
                        <div key={q.id} className={`card p-5 border-l-4 ${isSaved ? 'border-l-success-500' : 'border-l-gray-200'}`}>
                            <div className="flex items-start justify-between gap-3 mb-3">
                                <div>
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className="text-xs font-semibold text-gray-400">Question {i + 1}</span>
                                        <span className="badge bg-gray-100 text-gray-600">
                                            {QuestionKindLabels[q.question_kind] ?? q.question_kind}
                                        </span>
                                        <span className="badge bg-asecna-50 text-asecna-700">
                                            {q.points} pt{q.points > 1 ? 's' : ''}
                                        </span>
                                    </div>
                                    <p className="text-sm font-medium text-gray-900">{q.text}</p>
                                </div>
                                {isSaved && (
                                    <span className="text-xs text-success-600 flex items-center gap-1 shrink-0">
                                        <CheckCircle2 size={13} /> enregistrée
                                    </span>
                                )}
                            </div>

                            {/* QCM et Vrai/Faux proposent des choix ; la réponse ouverte
                                reste un champ libre, corrigé à la main par l'évaluateur. */}
                            {q.question_kind === 'MCQ' && q.options?.length > 0 ? (
                                <div className="space-y-2">
                                    {q.options.map((opt, oi) => (
                                        <label key={oi} className="flex items-center gap-2 text-sm cursor-pointer">
                                            <input
                                                type="radio"
                                                name={`q-${q.id}`}
                                                checked={current === opt}
                                                onChange={() => setDraft(d => ({ ...d, [q.id]: opt }))}
                                                className="accent-asecna-600"
                                            />
                                            <span>{opt}</span>
                                        </label>
                                    ))}
                                </div>
                            ) : q.question_kind === 'TF' ? (
                                <div className="flex gap-4">
                                    {['Vrai', 'Faux'].map(opt => (
                                        <label key={opt} className="flex items-center gap-2 text-sm cursor-pointer">
                                            <input
                                                type="radio"
                                                name={`q-${q.id}`}
                                                checked={current === opt}
                                                onChange={() => setDraft(d => ({ ...d, [q.id]: opt }))}
                                                className="accent-asecna-600"
                                            />
                                            <span>{opt}</span>
                                        </label>
                                    ))}
                                </div>
                            ) : (
                                <textarea
                                    value={current}
                                    onChange={(e) => setDraft(d => ({ ...d, [q.id]: e.target.value }))}
                                    rows={3}
                                    placeholder="Votre réponse…"
                                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-asecna-500"
                                />
                            )}

                            <button
                                onClick={() => answerMut.mutate({ question: q.id, response: current })}
                                disabled={!current.trim() || isSaved || answerMut.isPending || sessionId === null}
                                className="mt-3 px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-100 text-gray-700 hover:bg-gray-200 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5"
                            >
                                <Save size={13} /> {isSaved ? 'Réponse enregistrée' : 'Enregistrer cette réponse'}
                            </button>
                        </div>
                    )
                })
            )}
        </div>
    )
}
