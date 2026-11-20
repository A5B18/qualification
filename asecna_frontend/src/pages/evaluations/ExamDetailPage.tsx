/**
 * Composition d'un examen : banque de questions et publication.
 *
 * L'écran « Évaluations » permettait de créer un examen, mais aucun écran ne
 * permettait d'y rattacher des questions : l'examen créé restait vide, donc
 * inutilisable — un agent qui l'aurait démarré n'aurait eu aucun énoncé, et le
 * score se serait calculé sur un barème nul.
 *
 * Deux gestes ici :
 *   • créer une question dans la banque (EVALUATEUR / INSTRUCTEUR)
 *   • la rattacher ou la détacher de l'examen (relation ManyToMany, mise à
 *     jour par PATCH sur l'examen)
 */

import { useMemo, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
    ArrowLeft, Plus, X, Award, Check, Eye, EyeOff, Trash2, Search,
    AlertTriangle, ListChecks,
} from 'lucide-react'

import { evaluationsApi, trainingApi } from '../../api'
import { apiErrorMessage } from '../../api/client'
import { useAuth } from '../../store/authContextValue'
import {
    QuestionTypeLabels, ExamStatusLabels, ExamStatusColors,
    MCQ_MIN_OPTIONS, MCQ_MAX_OPTIONS,
    type Question, type Exam, type Training, type QuestionType,
    type User,
} from '../../types'
import { hasAnyRole } from '../../utils/roles'

/** Composition d'un examen — backend : `IsEvaluatorOrInstructor`. */
const canCompose = (user: User | null) => hasAnyRole(user, 'EVALUATOR', 'INSTRUCTOR')

/**
 * Formulaire de question — QCM uniquement.
 *
 * La bonne réponse n'est plus saisie librement : elle se désigne parmi les
 * options. Un champ libre laissait passer une « réponse attendue » absente
 * des propositions, et l'agent n'avait alors aucun moyen de répondre juste.
 * `correct_index` pointe la ligne retenue ; le texte est dérivé à l'envoi.
 */
const EMPTY_QUESTION = {
    text: '',
    question_type: 'TECHNICAL' as QuestionType,
    difficulty: 1,
    points: 10,
    correct_index: 0,
    options: ['', '', '', ''],
    training: '',
}

export default function ExamDetailPage() {
    const { id } = useParams<{ id: string }>()
    const examId = Number(id)
    const navigate = useNavigate()
    const qc = useQueryClient()
    const { user } = useAuth()
    const editable = canCompose(user)

    const [showForm, setShowForm] = useState(false)
    const [form, setForm] = useState(EMPTY_QUESTION)
    const [search, setSearch] = useState('')
    const [flash, setFlash] = useState<{ text: string; ok: boolean } | null>(null)

    const notify = (text: string, ok = true) => {
        setFlash({ text, ok })
        setTimeout(() => setFlash(null), 5000)
    }

    const { data: exam, isLoading } = useQuery<Exam>({
        queryKey: ['exam', examId],
        queryFn: () => evaluationsApi.exam(examId).then(r => r.data),
        enabled: Number.isFinite(examId),
    })

    const { data: bank } = useQuery<{ results: Question[] }>({
        queryKey: ['question-bank', search],
        queryFn: () => evaluationsApi
            .questions(search ? { search } : undefined)
            .then(r => r.data),
        enabled: editable,
    })

    const { data: trainingsData } = useQuery<{ results: Training[] }>({
        queryKey: ['trainings-select'],
        queryFn: () => trainingApi.trainings().then(r => r.data),
        enabled: showForm,
    })

    const attachedIds = useMemo(() => new Set(exam?.questions ?? []), [exam])
    const questions = bank?.results ?? []
    const attached = questions.filter(q => attachedIds.has(q.id))
    const available = questions.filter(q => !attachedIds.has(q.id))

    const totalPoints = attached.reduce((acc, q) => acc + q.points, 0)

    // Mêmes règles que `Question.clean()` côté serveur, annoncées avant
    // l'envoi plutôt que découvertes dans une réponse 400.
    const filledOptions = form.options.map(o => o.trim()).filter(Boolean)
    const chosenOption = (form.options[form.correct_index] ?? '').trim()
    const formError: string | null =
        form.text.trim() === ''
            ? "L'énoncé est obligatoire."
            : filledOptions.length < MCQ_MIN_OPTIONS
                ? `Un QCM doit proposer au moins ${MCQ_MIN_OPTIONS} options.`
                : new Set(filledOptions.map(o => o.toLowerCase())).size !== filledOptions.length
                    ? 'Deux options sont identiques.'
                    : chosenOption === ''
                        ? 'Cochez laquelle des options est la bonne réponse.'
                        : null

    const refresh = () => {
        qc.invalidateQueries({ queryKey: ['exam', examId] })
        qc.invalidateQueries({ queryKey: ['question-bank'] })
        qc.invalidateQueries({ queryKey: ['exams'] })
    }

    /** Le ManyToMany se met à jour en renvoyant la liste complète des ids. */
    const setQuestionsMut = useMutation({
        mutationFn: (ids: number[]) => evaluationsApi.updateExam(examId, { questions: ids }),
        onSuccess: () => { refresh(); notify('Composition mise à jour.') },
        onError: (err) => notify(apiErrorMessage(err, 'Mise à jour impossible.'), false),
    })

    const createQuestionMut = useMutation({
        mutationFn: async () => {
            const trimmed = form.options.map(o => o.trim())
            const created = await evaluationsApi.createQuestion({
                text: form.text,
                question_type: form.question_type,
                question_kind: 'MCQ',
                difficulty: Number(form.difficulty),
                points: Number(form.points),
                // La bonne réponse est l'option désignée, à la lettre : le
                // backend refuse une réponse absente des propositions.
                correct_answer: trimmed[form.correct_index] ?? '',
                options: trimmed.filter(Boolean),
                training: form.training ? Number(form.training) : null,
            })
            // Rattachement immédiat : une question créée depuis cet écran est
            // destinée à cet examen.
            const ids = [...(exam?.questions ?? []), created.data.id]
            await evaluationsApi.updateExam(examId, { questions: ids })
            return created.data
        },
        onSuccess: () => {
            refresh(); setShowForm(false); setForm(EMPTY_QUESTION)
            notify('Question créée et rattachée à l\'examen.')
        },
        onError: (err) => notify(apiErrorMessage(err, 'Création impossible.'), false),
    })

    const publishMut = useMutation({
        mutationFn: (publish: boolean) => publish
            ? evaluationsApi.publishExam(examId)
            : evaluationsApi.unpublishExam(examId),
        onSuccess: (_res, publish) => {
            refresh()
            notify(publish
                ? 'Examen publié — les agents peuvent le composer.'
                : 'Examen repassé en brouillon.')
        },
        onError: (err) => notify(apiErrorMessage(err, 'Opération impossible.'), false),
    })

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-asecna-600" />
            </div>
        )
    }

    if (!exam) {
        return (
            <div className="card text-center py-12 text-gray-500">
                Examen introuvable.
                <Link to="/evaluations" className="block text-asecna-600 text-sm mt-3">
                    Retour aux évaluations
                </Link>
            </div>
        )
    }

    const detach = (qid: number) =>
        setQuestionsMut.mutate((exam.questions ?? []).filter(x => x !== qid))
    const attach = (qid: number) =>
        setQuestionsMut.mutate([...(exam.questions ?? []), qid])

    return (
        <div className="space-y-5">
            <div className="flex items-start justify-between gap-4 flex-wrap">
                <div>
                    <button
                        onClick={() => navigate('/evaluations')}
                        className="text-sm text-gray-500 hover:text-gray-800 flex items-center gap-1 mb-2"
                    >
                        <ArrowLeft size={15} /> Évaluations
                    </button>
                    <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                        <Award size={22} className="text-asecna-600" /> {exam.title}
                    </h1>
                    <p className="text-sm text-gray-500 mt-1">
                        {exam.training_detail?.title ?? 'Sans formation rattachée'}
                        {' · '}Seuil {exam.passing_score}/100
                        {' · '}{attached.length} question(s), barème {totalPoints} points
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <span className={`badge ${ExamStatusColors[exam.exam_status]} text-sm px-3 py-1`}>
                        {ExamStatusLabels[exam.exam_status]}
                    </span>
                    {editable && (
                        exam.exam_status === 'PUBLISHED' ? (
                            <button
                                onClick={() => publishMut.mutate(false)}
                                className="px-3 py-2 rounded-lg text-sm bg-white border border-gray-200 text-gray-700 hover:bg-gray-50 flex items-center gap-1.5"
                            >
                                <EyeOff size={14} /> Dépublier
                            </button>
                        ) : (
                            <button
                                onClick={() => publishMut.mutate(true)}
                                disabled={attached.length === 0 || publishMut.isPending}
                                title={attached.length === 0
                                    ? 'Un examen sans question ne peut pas être publié'
                                    : 'Rendre l\'examen composable par les agents'}
                                className="px-3 py-2 rounded-lg text-sm bg-success-600 text-white hover:bg-success-700 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5"
                            >
                                <Eye size={14} /> Publier
                            </button>
                        )
                    )}
                </div>
            </div>

            {flash && (
                <div className={`rounded-lg px-4 py-3 text-sm ${flash.ok ? 'bg-success-50 text-success-800 border border-success-200' : 'bg-danger-50 text-danger-800 border border-danger-200'}`}>
                    {flash.text}
                </div>
            )}

            {!editable && (
                <div className="card text-sm text-gray-500">
                    La composition d'un examen est réservée aux évaluateurs et aux instructeurs.
                </div>
            )}

            {editable && (
                <>
                    {/* Questions rattachées */}
                    <div>
                        <div className="flex items-center justify-between mb-2">
                            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
                                Questions de l'examen ({attached.length})
                            </h2>
                            <button
                                onClick={() => setShowForm(v => !v)}
                                className="px-3 py-1.5 rounded-lg text-sm bg-asecna-600 text-white hover:bg-asecna-700 flex items-center gap-1.5"
                            >
                                {showForm ? <X size={14} /> : <Plus size={14} />}
                                {showForm ? 'Annuler' : 'Nouvelle question'}
                            </button>
                        </div>

                        {showForm && (
                            <form
                                onSubmit={(e) => { e.preventDefault(); createQuestionMut.mutate() }}
                                className="card p-5 space-y-3 mb-3"
                            >
                                <div>
                                    <label className="block text-xs font-medium text-gray-600 mb-1">Énoncé</label>
                                    <textarea
                                        required rows={2} value={form.text}
                                        aria-label="Énoncé"
                                        onChange={(e) => setForm(f => ({ ...f, text: e.target.value }))}
                                        className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-asecna-500"
                                    />
                                </div>

                                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                    <div>
                                        <label className="block text-xs font-medium text-gray-600 mb-1">Type</label>
                                        <select
                                            value={form.question_type}
                                            onChange={(e) => setForm(f => ({ ...f, question_type: e.target.value as QuestionType }))}
                                            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                                        >
                                            {Object.entries(QuestionTypeLabels).map(([k, v]) => (
                                                <option key={k} value={k}>{v}</option>
                                            ))}
                                        </select>
                                    </div>
                                    <div>
                                        <label className="block text-xs font-medium text-gray-600 mb-1">Format</label>
                                        <div className="w-full px-3 py-2 border border-gray-100 bg-gray-50 rounded-lg text-sm text-gray-500 flex items-center gap-1.5">
                                            <ListChecks size={13} /> QCM
                                        </div>
                                    </div>
                                    <div>
                                        <label className="block text-xs font-medium text-gray-600 mb-1">Difficulté (1-5)</label>
                                        <input
                                            type="number" min={1} max={5} value={form.difficulty}
                                            onChange={(e) => setForm(f => ({ ...f, difficulty: Number(e.target.value) }))}
                                            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-xs font-medium text-gray-600 mb-1">Points</label>
                                        <input
                                            type="number" min={1} value={form.points}
                                            onChange={(e) => setForm(f => ({ ...f, points: Number(e.target.value) }))}
                                            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                                        />
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-xs font-medium text-gray-600 mb-1">
                                        Options proposées — cochez la bonne réponse
                                    </label>
                                    <div className="space-y-2">
                                        {form.options.map((opt, i) => (
                                            <div key={i} className="flex items-center gap-2">
                                                <input
                                                    type="radio"
                                                    name="correct-option"
                                                    aria-label={`Option ${i + 1} : bonne réponse`}
                                                    checked={form.correct_index === i}
                                                    onChange={() => setForm(f => ({ ...f, correct_index: i }))}
                                                    className="accent-success-600 shrink-0"
                                                />
                                                <input
                                                    value={opt}
                                                    placeholder={`Option ${i + 1}`}
                                                    onChange={(e) => setForm(f => ({
                                                        ...f,
                                                        options: f.options.map((o, oi) => oi === i ? e.target.value : o),
                                                    }))}
                                                    className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm"
                                                />
                                                {form.options.length > MCQ_MIN_OPTIONS && (
                                                    <button
                                                        type="button"
                                                        title="Retirer cette option"
                                                        onClick={() => setForm(f => {
                                                            const options = f.options.filter((_, oi) => oi !== i)
                                                            // L'index suit la ligne retirée, sinon la
                                                            // coche se déplacerait sur une autre option.
                                                            const correct = f.correct_index > i
                                                                ? f.correct_index - 1
                                                                : Math.min(f.correct_index, options.length - 1)
                                                            return { ...f, options, correct_index: Math.max(correct, 0) }
                                                        })}
                                                        className="shrink-0 p-2 rounded-lg text-gray-400 hover:text-danger-600 hover:bg-danger-50"
                                                    >
                                                        <X size={14} />
                                                    </button>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                    {form.options.length < MCQ_MAX_OPTIONS && (
                                        <button
                                            type="button"
                                            onClick={() => setForm(f => ({ ...f, options: [...f.options, ''] }))}
                                            className="mt-2 text-xs text-asecna-700 hover:underline flex items-center gap-1"
                                        >
                                            <Plus size={12} /> Ajouter une option
                                        </button>
                                    )}
                                </div>

                                <div>
                                    <label className="block text-xs font-medium text-gray-600 mb-1">
                                        Formation (facultatif)
                                    </label>
                                    <select
                                        value={form.training}
                                        onChange={(e) => setForm(f => ({ ...f, training: e.target.value }))}
                                        className="w-full md:w-1/2 px-3 py-2 border border-gray-200 rounded-lg text-sm"
                                    >
                                        <option value="">—</option>
                                        {(trainingsData?.results ?? []).map(t => (
                                            <option key={t.id} value={t.id}>{t.title}</option>
                                        ))}
                                    </select>
                                </div>

                                {/* Les mêmes règles que le serveur, annoncées avant l'envoi. */}
                                {formError && (
                                    <p className="text-xs text-danger-600 flex items-center gap-1">
                                        <AlertTriangle size={12} /> {formError}
                                    </p>
                                )}

                                <button
                                    type="submit"
                                    disabled={createQuestionMut.isPending || formError !== null}
                                    className="px-4 py-2 rounded-lg text-sm font-medium bg-asecna-600 text-white hover:bg-asecna-700 disabled:opacity-40"
                                >
                                    Créer et rattacher
                                </button>
                            </form>
                        )}

                        {attached.length === 0 ? (
                            <div className="card text-center py-8 text-gray-400 text-sm">
                                Aucune question rattachée. Un examen vide ne peut pas être publié.
                            </div>
                        ) : (
                            <div className="space-y-2">
                                {attached.map((q, i) => (
                                    <div key={q.id} className="card p-4 flex items-start justify-between gap-3">
                                        <div className="min-w-0">
                                            <div className="flex items-center gap-2 mb-1 flex-wrap">
                                                <span className="text-xs font-semibold text-gray-400">Q{i + 1}</span>
                                                <span className="badge bg-gray-100 text-gray-600">
                                                    QCM · {q.options?.length ?? 0} options
                                                </span>
                                                <span className="badge bg-asecna-50 text-asecna-700">{q.points} pt</span>
                                                <span className="badge bg-gray-100 text-gray-500">
                                                    difficulté {q.difficulty}
                                                </span>
                                            </div>
                                            <p className="text-sm text-gray-900">{q.text}</p>
                                            {/* Les propositions telles que l'agent les verra,
                                                la bonne réponse mise en évidence. */}
                                            {(q.options?.length ?? 0) > 0 && (
                                                <ul className="mt-1.5 space-y-0.5">
                                                    {q.options.map((opt, oi) => {
                                                        const correct = q.correct_answer?.trim().toLowerCase()
                                                            === opt.trim().toLowerCase()
                                                        return (
                                                            <li key={oi}
                                                                className={`text-xs flex items-center gap-1.5 ${correct ? 'text-success-700 font-medium' : 'text-gray-500'}`}>
                                                                {correct
                                                                    ? <Check size={12} className="shrink-0" />
                                                                    : <span className="w-3 shrink-0" />}
                                                                {opt}
                                                            </li>
                                                        )
                                                    })}
                                                </ul>
                                            )}
                                        </div>
                                        <button
                                            onClick={() => detach(q.id)}
                                            disabled={setQuestionsMut.isPending}
                                            title="Retirer de cet examen"
                                            className="shrink-0 p-2 rounded-lg text-gray-400 hover:text-danger-600 hover:bg-danger-50"
                                        >
                                            <Trash2 size={15} />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Banque de questions */}
                    <div>
                        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
                            Banque de questions ({available.length} disponible(s))
                        </h2>
                        <div className="card p-3 mb-2">
                            <div className="relative">
                                <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                                <input
                                    value={search}
                                    onChange={(e) => setSearch(e.target.value)}
                                    placeholder="Rechercher dans les énoncés…"
                                    className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-asecna-500"
                                />
                            </div>
                        </div>

                        {available.length === 0 ? (
                            <div className="card text-center py-6 text-gray-400 text-sm">
                                Aucune question disponible à rattacher.
                            </div>
                        ) : (
                            <div className="space-y-2">
                                {available.map(q => (
                                    <div key={q.id} className="card p-3 flex items-center justify-between gap-3">
                                        <div className="min-w-0">
                                            <p className="text-sm text-gray-800 truncate">{q.text}</p>
                                            <p className="text-xs text-gray-400">
                                                {QuestionTypeLabels[q.question_type]} · {q.points} pt
                                                {' · '}QCM {q.options?.length ?? 0} options
                                            </p>
                                        </div>
                                        <button
                                            onClick={() => attach(q.id)}
                                            disabled={setQuestionsMut.isPending}
                                            className="shrink-0 px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-100 text-gray-700 hover:bg-gray-200 flex items-center gap-1.5"
                                        >
                                            <Check size={13} /> Rattacher
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </>
            )}
        </div>
    )
}
