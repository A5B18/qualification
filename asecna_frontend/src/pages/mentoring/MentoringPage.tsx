import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
    BookOpen, ExternalLink, CheckCircle, XCircle,
    Clock, ThumbsUp, ThumbsDown, Eye, X, AlertTriangle,
} from 'lucide-react'
import { mentoringApi } from '../../api'
import { useAuth } from '../../store/authContextValue'
import {
    MentoringStatusLabels, MentoringStatusColors,
    type MentoringStatus, type MentoringRecord, type User,
} from '../../types'
import { apiErrorMessage } from '../../api/client'

function canApprove(user: User | null): boolean {
    const r: string[] = user?.roles ?? []
    return user?.is_superuser || r.includes('ADMIN') || r.includes('UNIT_CHIEF') || r.includes('APPROVER')
}

function fmt(d: string | null | undefined) {
    return d ? new Date(d).toLocaleDateString('fr-FR') : '—'
}

const STATUS_ICONS: Record<MentoringStatus, React.ReactNode> = {
    DRAFT:     <Clock size={12} />,
    SUBMITTED: <AlertTriangle size={12} />,
    APPROVED:  <CheckCircle size={12} />,
    REJECTED:  <XCircle size={12} />,
    COMPLETED: <CheckCircle size={12} />,
}

export default function MentoringPage() {
    const { user } = useAuth()
    const qc = useQueryClient()

    const [filterStatus, setFilterStatus] = useState('ALL')
    const [detailId, setDetailId]         = useState<number | null>(null)
    const [rejectId, setRejectId]         = useState<number | null>(null)
    const [rejectOpinion, setRejectOpinion] = useState('')
    const [flash, setFlash] = useState<{ text: string; ok: boolean } | null>(null)

    const notify = (text: string, ok = true) => {
        setFlash({ text, ok })
        setTimeout(() => setFlash(null), 4000)
    }

    // ── Queries ──────────────────────────────────────────────────────────────
    const { data, isLoading } = useQuery({
        queryKey: ['mentorings', filterStatus],
        queryFn: () => mentoringApi.list(
            filterStatus !== 'ALL' ? { mentoring_status: filterStatus } : {}
        ).then(r => r.data),
    })

    const records: MentoringRecord[] = data?.results ?? []

    // Compteurs par statut (sur la totalité, sans filtre)
    const { data: allData } = useQuery({
        queryKey: ['mentorings-counts'],
        queryFn: () => mentoringApi.list().then(r => r.data),
    })
    const all: MentoringRecord[] = allData?.results ?? []
    const counts = (['DRAFT','SUBMITTED','APPROVED','REJECTED','COMPLETED'] as MentoringStatus[])
        .reduce((acc, s) => ({ ...acc, [s]: all.filter(r => r.mentoring_status === s).length }), {} as Record<MentoringStatus, number>)

    const selectedRecord = detailId ? records.find(r => r.id === detailId) ?? all.find(r => r.id === detailId) : null

    // ── Mutations ─────────────────────────────────────────────────────────────
    const approveMut = useMutation({
        mutationFn: ({ id, opinion }: { id: number; opinion: string }) =>
            mentoringApi.approve(id, { unit_chief_opinion: opinion }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['mentorings'] })
            qc.invalidateQueries({ queryKey: ['mentorings-counts'] })
            setDetailId(null)
            notify('✅ Fiche de mentorat approuvée')
        },
        onError: (e: unknown) => notify(apiErrorMessage(e, '❌ Erreur'), false),
    })

    const rejectMut = useMutation({
        mutationFn: ({ id, opinion }: { id: number; opinion: string }) =>
            mentoringApi.reject(id, { unit_chief_opinion: opinion }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['mentorings'] })
            qc.invalidateQueries({ queryKey: ['mentorings-counts'] })
            setRejectId(null)
            setRejectOpinion('')
            notify('Fiche rejetée — le mentor doit la corriger')
        },
        onError: (e: unknown) => notify(apiErrorMessage(e, '❌ Erreur'), false),
    })

    const submitMut = useMutation({
        mutationFn: ({ id, data }: { id: number; data: Record<string, unknown> }) =>
            mentoringApi.submit(id, data),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['mentorings'] })
            qc.invalidateQueries({ queryKey: ['mentorings-counts'] })
            setDetailId(null)
            notify('📤 Fiche soumise au chef d\'unité')
        },
        onError: (e: unknown) => notify(apiErrorMessage(e, '❌ Erreur'), false),
    })

    const pending = all.filter(r => r.mentoring_status === 'SUBMITTED')

    return (
        <div className="space-y-6">
            {/* ── En-tête ── */}
            <div>
                <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                    <BookOpen size={24} className="text-indigo-600" /> Fiches de Mentorat
                </h1>
                <p className="text-gray-400 text-sm mt-0.5">
                    {allData?.count ?? 0} fiche{(allData?.count ?? 0) > 1 ? 's' : ''} enregistrée{(allData?.count ?? 0) > 1 ? 's' : ''}
                </p>
            </div>

            {/* ── Flash ── */}
            {flash && (
                <div className={`p-3 rounded-xl text-sm font-medium border flex items-center justify-between ${
                    flash.ok ? 'bg-green-50 border-green-200 text-green-800' : 'bg-red-50 border-red-200 text-red-800'
                }`}>
                    {flash.text}
                    <button onClick={() => setFlash(null)}><X size={14} /></button>
                </div>
            )}

            {/* ── Alerte : fiches en attente d'approbation ── */}
            {canApprove(user) && pending.length > 0 && (
                <div className="card border-l-4 border-yellow-400 bg-yellow-50 py-3">
                    <p className="text-yellow-800 text-sm font-medium flex items-center gap-2">
                        <AlertTriangle size={16} className="text-yellow-500" />
                        {pending.length} fiche{pending.length > 1 ? 's' : ''} en attente de votre approbation
                    </p>
                </div>
            )}

            {/* ── KPIs cliquables ── */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                {(['DRAFT','SUBMITTED','APPROVED','REJECTED','COMPLETED'] as MentoringStatus[]).map(s => (
                    <button
                        key={s}
                        onClick={() => setFilterStatus(filterStatus === s ? 'ALL' : s)}
                        className={`card text-center py-4 transition-all hover:shadow-md ${
                            filterStatus === s ? 'ring-2 ring-indigo-400 ring-offset-1' : ''
                        }`}
                    >
                        <div className="text-2xl font-bold text-gray-900">{counts[s] ?? 0}</div>
                        <span className={`badge mt-1.5 flex items-center justify-center gap-1 ${MentoringStatusColors[s]}`}>
                            {STATUS_ICONS[s]}{MentoringStatusLabels[s]}
                        </span>
                    </button>
                ))}
            </div>

            {/* ── Filtre actif ── */}
            {filterStatus !== 'ALL' && (
                <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-500">Filtre :</span>
                    <span className={`badge flex items-center gap-1 ${MentoringStatusColors[filterStatus as MentoringStatus]}`}>
                        {MentoringStatusLabels[filterStatus as MentoringStatus]}
                    </span>
                    <button onClick={() => setFilterStatus('ALL')} className="text-xs text-gray-400 hover:text-gray-600 underline ml-1">
                        Effacer
                    </button>
                </div>
            )}

            {/* ── Tableau ── */}
            <div className="card p-0 overflow-hidden">
                {isLoading ? (
                    <div className="flex items-center justify-center h-40">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
                    </div>
                ) : records.length === 0 ? (
                    <div className="text-center py-14 text-gray-400">
                        <BookOpen size={40} className="mx-auto mb-2 opacity-25" />
                        <p className="text-sm">Aucune fiche de mentorat{filterStatus !== 'ALL' ? ' avec ce statut' : ''}</p>
                    </div>
                ) : (
                    <table className="w-full text-sm">
                        <thead className="bg-gray-50 border-b border-gray-100">
                            <tr>
                                {['Agent mentoré','Mentor','Début','Fin','Objectifs','Statut','Actions'].map(h => (
                                    <th key={h} className="text-left px-5 py-3 text-gray-500 font-medium text-xs uppercase tracking-wider">
                                        {h}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-50">
                            {records.map((r: MentoringRecord) => {
                                const st = r.mentoring_status as MentoringStatus
                                const isPending = st === 'SUBMITTED'
                                return (
                                    <tr key={r.id} className={`hover:bg-gray-50 transition-colors ${isPending && canApprove(user) ? 'bg-yellow-50/30' : ''}`}>
                                        {/* Agent */}
                                        <td className="px-5 py-3.5">
                                            <Link to={`/agents/${r.agent}`} className="flex items-center gap-1 font-medium text-indigo-700 hover:underline">
                                                {r.agent_detail?.first_name} {r.agent_detail?.last_name}
                                                <ExternalLink size={11} />
                                            </Link>
                                            <div className="text-xs text-gray-400">{r.agent_detail?.matricule ?? `#${r.agent}`}</div>
                                        </td>

                                        {/* Mentor */}
                                        <td className="px-5 py-3.5 text-gray-600">
                                            {r.mentor_detail
                                                ? <Link to={`/agents/${r.mentor}`} className="hover:underline text-gray-700">
                                                    {r.mentor_detail.first_name} {r.mentor_detail.last_name}
                                                  </Link>
                                                : <span className="text-gray-300">—</span>}
                                        </td>

                                        {/* Dates */}
                                        <td className="px-5 py-3.5 text-gray-500">{fmt(r.start_date)}</td>
                                        <td className="px-5 py-3.5 text-gray-500">{fmt(r.end_date)}</td>

                                        {/* Objectifs */}
                                        <td className="px-5 py-3.5 text-gray-500 max-w-[200px]">
                                            <p className="truncate" title={r.objectives}>{r.objectives || '—'}</p>
                                        </td>

                                        {/* Statut */}
                                        <td className="px-5 py-3.5">
                                            <span className={`badge flex items-center gap-1 w-fit ${MentoringStatusColors[st]}`}>
                                                {STATUS_ICONS[st]}{MentoringStatusLabels[st]}
                                            </span>
                                        </td>

                                        {/* Actions */}
                                        <td className="px-5 py-3.5">
                                            <div className="flex items-center gap-2">
                                                <button
                                                    onClick={() => setDetailId(r.id)}
                                                    className="p-1.5 rounded-lg hover:bg-indigo-50 text-indigo-400 hover:text-indigo-600 transition-colors"
                                                    title="Voir détails"
                                                >
                                                    <Eye size={15} />
                                                </button>
                                                {isPending && canApprove(user) && (
                                                    <>
                                                        <button
                                                            onClick={() => approveMut.mutate({ id: r.id, opinion: '' })}
                                                            disabled={approveMut.isPending}
                                                            className="p-1.5 rounded-lg hover:bg-green-50 text-green-400 hover:text-green-600 transition-colors"
                                                            title="Approuver"
                                                        >
                                                            <ThumbsUp size={15} />
                                                        </button>
                                                        <button
                                                            onClick={() => { setRejectId(r.id); setRejectOpinion('') }}
                                                            className="p-1.5 rounded-lg hover:bg-red-50 text-red-400 hover:text-red-500 transition-colors"
                                                            title="Rejeter"
                                                        >
                                                            <ThumbsDown size={15} />
                                                        </button>
                                                    </>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                )
                            })}
                        </tbody>
                    </table>
                )}
            </div>

            {/* ── Modal : Détail fiche ── */}
            {detailId !== null && selectedRecord && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
                    <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
                        <div className="flex items-center justify-between mb-5">
                            <div>
                                <h3 className="text-lg font-bold text-gray-900">Fiche de mentorat</h3>
                                <p className="text-sm text-gray-400 mt-0.5">
                                    {selectedRecord.agent_detail?.matricule} — {selectedRecord.agent_detail?.first_name} {selectedRecord.agent_detail?.last_name}
                                </p>
                            </div>
                            <button onClick={() => setDetailId(null)} className="p-1.5 hover:bg-gray-100 rounded-lg text-gray-400">
                                <X size={18} />
                            </button>
                        </div>

                        {/* Statut */}
                        <div className="mb-4">
                            <span className={`badge ${MentoringStatusColors[selectedRecord.mentoring_status]}`}>
                                {MentoringStatusLabels[selectedRecord.mentoring_status]}
                            </span>
                        </div>

                        {/* Info grid */}
                        <div className="grid grid-cols-2 gap-4 mb-5 text-sm">
                            <div>
                                <p className="text-gray-400 text-xs mb-0.5">Mentor</p>
                                <p className="font-medium text-gray-900">
                                    {selectedRecord.mentor_detail?.first_name} {selectedRecord.mentor_detail?.last_name}
                                </p>
                            </div>
                            <div>
                                <p className="text-gray-400 text-xs mb-0.5">Chef d'unité</p>
                                <p className="font-medium text-gray-900">
                                    {selectedRecord.unit_chief_detail?.full_name ?? '—'}
                                </p>
                            </div>
                            <div>
                                <p className="text-gray-400 text-xs mb-0.5">Début</p>
                                <p className="font-medium text-gray-900">{fmt(selectedRecord.start_date)}</p>
                            </div>
                            <div>
                                <p className="text-gray-400 text-xs mb-0.5">Fin</p>
                                <p className="font-medium text-gray-900">{fmt(selectedRecord.end_date)}</p>
                            </div>
                        </div>

                        {/* Sections texte */}
                        {[
                            { label: 'Objectifs', value: selectedRecord.objectives },
                            { label: 'Observations du mentor', value: selectedRecord.mentor_observations },
                            { label: 'Avis final du mentor', value: selectedRecord.mentor_opinion },
                            { label: "Avis du chef d'unité", value: selectedRecord.unit_chief_opinion },
                        ].map(({ label, value }) => value ? (
                            <div key={label} className="mb-4">
                                <p className="text-xs text-gray-400 font-medium mb-1">{label}</p>
                                <div className="bg-gray-50 rounded-xl p-3 text-sm text-gray-700 whitespace-pre-wrap">{value}</div>
                            </div>
                        ) : null)}

                        {/* Actions pour chef d'unité */}
                        {selectedRecord.mentoring_status === 'SUBMITTED' && canApprove(user) && (
                            <div className="flex gap-3 mt-5 pt-4 border-t border-gray-100">
                                <button
                                    onClick={() => approveMut.mutate({ id: selectedRecord.id, opinion: '' })}
                                    disabled={approveMut.isPending}
                                    className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded-xl transition-colors disabled:opacity-50"
                                >
                                    <ThumbsUp size={15} /> Approuver
                                </button>
                                <button
                                    onClick={() => { setRejectId(selectedRecord.id); setDetailId(null); setRejectOpinion('') }}
                                    className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-500 hover:bg-red-600 rounded-xl transition-colors"
                                >
                                    <ThumbsDown size={15} /> Rejeter
                                </button>
                            </div>
                        )}

                        {/* Action soumettre (mentor / draft) */}
                        {selectedRecord.mentoring_status === 'DRAFT' && (
                            <div className="mt-5 pt-4 border-t border-gray-100">
                                <button
                                    onClick={() => submitMut.mutate({ id: selectedRecord.id, data: {} })}
                                    disabled={submitMut.isPending}
                                    className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl transition-colors disabled:opacity-50"
                                >
                                    {submitMut.isPending ? 'Soumission…' : '📤 Soumettre au chef d\'unité'}
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* ── Modal : Rejeter ── */}
            {rejectId !== null && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
                    <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-md">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-bold text-gray-900">Motif de rejet</h3>
                            <button onClick={() => setRejectId(null)} className="p-1.5 hover:bg-gray-100 rounded-lg text-gray-400">
                                <X size={18} />
                            </button>
                        </div>
                        <textarea
                            className="w-full border border-gray-200 rounded-xl p-3 text-sm min-h-[100px] resize-none focus:outline-none focus:ring-2 focus:ring-red-400"
                            placeholder="Expliquer pourquoi la fiche est rejetée (obligatoire)..."
                            value={rejectOpinion}
                            onChange={e => setRejectOpinion(e.target.value)}
                        />
                        <div className="flex gap-3 mt-4 justify-end">
                            <button onClick={() => setRejectId(null)} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-xl">
                                Annuler
                            </button>
                            <button
                                onClick={() => rejectId && rejectMut.mutate({ id: rejectId, opinion: rejectOpinion })}
                                disabled={!rejectOpinion.trim() || rejectMut.isPending}
                                className="px-4 py-2 text-sm text-white bg-red-600 hover:bg-red-700 rounded-xl disabled:opacity-40 transition-colors"
                            >
                                {rejectMut.isPending ? 'Rejet…' : 'Confirmer le rejet'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
