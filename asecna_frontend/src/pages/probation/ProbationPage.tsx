import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { probationApi, agentsApi } from '../../api'
import { useAuth } from '../../store/authContextValue'
import {
    ClipboardList, AlertTriangle, CheckCircle, X,
    Plus, Star,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { useState } from 'react'
import { apiErrorMessage } from '../../api/client'
import { useNow, daysUntil, isWithinAlertWindow } from '../../utils/dates'

const STATUS_LABELS: Record<string, string> = {
    IN_PROGRESS: 'En cours', PASSED: 'Réussie ✓', FAILED: 'Échouée',
}
const STATUS_COLORS: Record<string, string> = {
    IN_PROGRESS: 'bg-blue-100 text-blue-700',
    PASSED: 'bg-green-100 text-green-700',
    FAILED: 'bg-red-100 text-red-700',
}

function canCreate(user: any) {
    const r: string[] = user?.roles ?? []
    return user?.is_superuser || r.includes('ADMIN') || r.includes('UNIT_CHIEF')
}
function canFinalize(user: any) {
    const r: string[] = user?.roles ?? []
    return user?.is_superuser || r.includes('ADMIN') || r.includes('EVALUATOR') || r.includes('UNIT_CHIEF')
}

export default function ProbationPage() {
    const { user } = useAuth()
    const qc = useQueryClient()
    // Référence temporelle figée : évite que deux lignes du tableau soient
    // calculées sur des instants différents (et le calcul reste pur)
    const now = useNow()

    const [statusFilter, setStatusFilter] = useState('ALL')
    const [showCreate, setShowCreate] = useState(false)
    const [finalizeId, setFinalizeId] = useState<number | null>(null)
    const [score, setScore] = useState<number>(70)
    const [comment, setComment] = useState('')
    const [flash, setFlash] = useState<{ text: string; ok: boolean } | null>(null)
    const [createForm, setCreateForm] = useState({ agent: '', start_date: '', end_date: '' })

    const notify = (text: string, ok = true) => {
        setFlash({ text, ok })
        setTimeout(() => setFlash(null), 4000)
    }

    const { data, isLoading } = useQuery({
        queryKey: ['probations-all', statusFilter],
        queryFn: () => probationApi.list(statusFilter !== 'ALL' ? { probation_status: statusFilter } : {}).then(r => r.data),
    })
    const { data: agentsData } = useQuery({
        queryKey: ['agents-select-prob'],
        queryFn: () => agentsApi.list().then(r => r.data),
        enabled: showCreate,
    })

    const probations = data?.results ?? []
    const agents = agentsData?.results ?? []
    const inProgress = probations.filter((p: any) => p.probation_status === 'IN_PROGRESS').length
    const passed = probations.filter((p: any) => p.probation_status === 'PASSED').length
    const failed = probations.filter((p: any) => p.probation_status === 'FAILED').length

    const createMut = useMutation({
        mutationFn: (data: any) => probationApi.create({ ...data, agent: Number(data.agent), attempt_number: 1 }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['probations-all'] })
            setShowCreate(false)
            setCreateForm({ agent: '', start_date: '', end_date: '' })
            notify('✅ Période d\'essai créée')
        },
        onError: (e: unknown) => notify(apiErrorMessage(e, '❌ Erreur lors de la création'), false),
    })

    const finalizeMut = useMutation({
        mutationFn: ({ id, score, comment }: { id: number; score: number; comment: string }) =>
            probationApi.finalize(id, { score, unit_chief_comment: comment }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['probations-all'] })
            setFinalizeId(null)
            notify(`✅ Évaluation enregistrée — Score : ${score}/100`)
        },
        onError: (e: unknown) => notify(apiErrorMessage(e, '❌ Erreur lors de la finalisation'), false),
    })

    const dueAlert = probations.filter((p: any) => {
        if (p.probation_status !== 'IN_PROGRESS') return false
        return isWithinAlertWindow(daysUntil(p.end_date, now))
    })

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                        <ClipboardList size={24} className="text-amber-600" /> Périodes d'essai
                    </h1>
                    <p className="text-gray-400 text-sm mt-0.5">{data?.count ?? 0} périodes enregistrées</p>
                </div>
                {canCreate(user) && (
                    <button onClick={() => setShowCreate(true)}
                        className="flex items-center gap-2 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-xl text-sm font-medium transition-colors">
                        <Plus size={16} /> Nouvelle période
                    </button>
                )}
            </div>

            {flash && (
                <div className={`p-3 rounded-xl text-sm border ${flash.ok ? 'bg-green-50 border-green-200 text-green-800' : 'bg-red-50 border-red-200 text-red-800'}`}>
                    {flash.text}
                </div>
            )}

            {/* Alerte J-14 */}
            {dueAlert.length > 0 && (
                <div className="flex items-center gap-3 p-3 bg-red-50 border-l-4 border-red-500 rounded-xl text-sm">
                    <AlertTriangle size={16} className="text-red-600 flex-shrink-0" />
                    <span className="text-red-800 font-medium">
                        ⚠️ {dueAlert.length} période(s) d'essai se terminent dans moins de 14 jours — Évaluation requise !
                    </span>
                </div>
            )}

            {/* KPIs */}
            <div className="grid grid-cols-3 gap-4">
                {[
                    { label: 'En cours', value: inProgress, s: 'IN_PROGRESS', color: 'bg-blue-50 border-blue-200 text-blue-700' },
                    { label: 'Réussies', value: passed, s: 'PASSED', color: 'bg-green-50 border-green-200 text-green-700' },
                    { label: 'Échouées', value: failed, s: 'FAILED', color: 'bg-red-50 border-red-200 text-red-700' },
                ].map(({ label, value, s, color }) => (
                    <button key={s} onClick={() => setStatusFilter(statusFilter === s ? 'ALL' : s)}
                        className={`rounded-xl border p-4 text-left transition-all ${color} ${statusFilter === s ? 'ring-2 ring-offset-1 ring-amber-400' : ''}`}>
                        <div className="text-2xl font-bold">{value}</div>
                        <div className="text-sm">{label}</div>
                    </button>
                ))}
            </div>

            {/* Table */}
            <div className="card p-0 overflow-hidden">
                {isLoading ? (
                    <div className="flex items-center justify-center h-40">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-amber-600" />
                    </div>
                ) : probations.length === 0 ? (
                    <div className="text-center py-12 text-gray-400">
                        <ClipboardList size={40} className="mx-auto mb-2 opacity-30" />
                        <p>Aucune période d'essai enregistrée</p>
                    </div>
                ) : (
                    <table className="w-full text-sm">
                        <thead className="bg-gray-50 border-b border-gray-100">
                            <tr>
                                {['Agent', 'Tentative', 'Début', 'Fin', 'Jours restants', 'Score', 'Statut', 'Actions'].map(h => (
                                    <th key={h} className="text-left px-5 py-3 text-gray-500 font-medium text-xs uppercase tracking-wide">{h}</th>
                                ))}
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-50">
                            {probations.map((p: any) => {
                                const daysLeft = daysUntil(p.end_date, now)
                                const urgent = isWithinAlertWindow(daysLeft) && p.probation_status === 'IN_PROGRESS'
                                return (
                                    <tr key={p.id} className={`hover:bg-gray-50 ${urgent ? 'bg-red-50/50' : ''}`}>
                                        <td className="px-5 py-3.5">
                                            <Link to={`/agents/${p.agent}`} className="font-medium text-asecna-700 hover:underline font-mono text-xs">
                                                {p.agent_detail?.matricule ?? `#${p.agent}`}
                                            </Link>
                                            <div className="text-xs text-gray-400">
                                                {p.agent_detail?.first_name} {p.agent_detail?.last_name}
                                            </div>
                                        </td>
                                        <td className="px-5 py-3.5 text-gray-600">#{p.attempt_number}</td>
                                        <td className="px-5 py-3.5 text-gray-600">{new Date(p.start_date).toLocaleDateString('fr-FR')}</td>
                                        <td className="px-5 py-3.5 text-gray-600">{new Date(p.end_date).toLocaleDateString('fr-FR')}</td>
                                        <td className="px-5 py-3.5">
                                            {p.probation_status === 'IN_PROGRESS' && daysLeft > 0 ? (
                                                <span className={`font-bold ${urgent ? 'text-red-600' : daysLeft < 30 ? 'text-orange-500' : 'text-gray-600'}`}>
                                                    {urgent && '⚠️ '}{daysLeft}j
                                                </span>
                                            ) : '—'}
                                        </td>
                                        <td className="px-5 py-3.5">
                                            {p.score != null ? (
                                                <span className={`font-semibold flex items-center gap-1 ${p.score >= 70 ? 'text-green-600' : 'text-red-500'}`}>
                                                    <Star size={12} /> {p.score}/100
                                                </span>
                                            ) : '—'}
                                        </td>
                                        <td className="px-5 py-3.5">
                                            <span className={`badge text-xs ${STATUS_COLORS[p.probation_status]}`}>
                                                {STATUS_LABELS[p.probation_status]}
                                            </span>
                                        </td>
                                        <td className="px-5 py-3.5">
                                            {p.probation_status === 'IN_PROGRESS' && canFinalize(user) && (
                                                <button
                                                    onClick={() => { setFinalizeId(p.id); setScore(70); setComment('') }}
                                                    className="text-xs flex items-center gap-1 px-2 py-1 bg-amber-100 text-amber-700 hover:bg-amber-200 rounded-lg">
                                                    <CheckCircle size={11} /> Évaluer
                                                </button>
                                            )}
                                        </td>
                                    </tr>
                                )
                            })}
                        </tbody>
                    </table>
                )}
            </div>

            {/* Modal : Créer */}
            {showCreate && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
                    <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-md">
                        <div className="flex items-center justify-between mb-5">
                            <h3 className="text-lg font-bold text-gray-900">Nouvelle période d'essai</h3>
                            <button onClick={() => setShowCreate(false)} className="p-1 hover:bg-gray-100 rounded-lg"><X size={18} className="text-gray-400" /></button>
                        </div>
                        <form onSubmit={e => { e.preventDefault(); createMut.mutate(createForm) }} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Agent *</label>
                                <select required value={createForm.agent} onChange={e => setCreateForm(f => ({ ...f, agent: e.target.value }))}
                                    className="w-full border border-gray-200 rounded-xl p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber-500">
                                    <option value="">— Choisir —</option>
                                    {agents.map((a: any) => (
                                        <option key={a.id} value={a.id}>{a.first_name} {a.last_name} ({a.matricule})</option>
                                    ))}
                                </select>
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Date début *</label>
                                    <input required type="date" value={createForm.start_date}
                                        onChange={e => setCreateForm(f => ({ ...f, start_date: e.target.value }))}
                                        className="w-full border border-gray-200 rounded-xl p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber-500" />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Date fin *</label>
                                    <input required type="date" value={createForm.end_date}
                                        onChange={e => setCreateForm(f => ({ ...f, end_date: e.target.value }))}
                                        className="w-full border border-gray-200 rounded-xl p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber-500" />
                                </div>
                            </div>
                            <div className="flex gap-3 justify-end pt-2">
                                <button type="button" onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-xl">Annuler</button>
                                <button type="submit" disabled={createMut.isPending}
                                    className="px-4 py-2 text-sm font-medium text-white bg-amber-600 hover:bg-amber-700 rounded-xl disabled:opacity-50">
                                    {createMut.isPending ? 'Création...' : 'Créer'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Modal : Finaliser / Évaluer */}
            {finalizeId !== null && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
                    <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-md">
                        <div className="flex items-center justify-between mb-5">
                            <h3 className="text-lg font-bold text-gray-900">Évaluation de la période d'essai</h3>
                            <button onClick={() => setFinalizeId(null)} className="p-1 hover:bg-gray-100 rounded-lg"><X size={18} className="text-gray-400" /></button>
                        </div>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Score final : <span className={`font-bold text-lg ${score >= 70 ? 'text-green-600' : 'text-red-500'}`}>{score}/100</span>
                                    {score < 70 && <span className="ml-2 text-xs text-red-500">(Échec — seuil 70/100)</span>}
                                </label>
                                <input type="range" min={0} max={100} value={score}
                                    onChange={e => setScore(Number(e.target.value))}
                                    className="w-full accent-amber-500" />
                                <div className="flex justify-between text-xs text-gray-400 mt-1">
                                    <span>0</span><span>50</span><span>100</span>
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Commentaire</label>
                                <textarea value={comment} onChange={e => setComment(e.target.value)}
                                    rows={3} placeholder="Observations sur la période d'essai..."
                                    className="w-full border border-gray-200 rounded-xl p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-amber-500" />
                            </div>
                            {score >= 70 ? (
                                <div className="p-3 bg-green-50 border border-green-200 rounded-xl text-sm text-green-700">
                                    ✅ L'agent sera marqué comme <strong>Réussi</strong> — statut mis à jour.
                                </div>
                            ) : (
                                <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
                                    ⚠️ Score inférieur à 70/100 — La période d'essai sera marquée comme <strong>Échouée</strong>.
                                </div>
                            )}
                        </div>
                        <div className="flex gap-3 mt-5 justify-end">
                            <button onClick={() => setFinalizeId(null)} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-xl">Annuler</button>
                            <button
                                disabled={finalizeMut.isPending}
                                onClick={() => finalizeMut.mutate({ id: finalizeId!, score, comment })}
                                className="px-4 py-2 text-sm font-medium text-white bg-amber-600 hover:bg-amber-700 rounded-xl disabled:opacity-50">
                                {finalizeMut.isPending ? 'Enregistrement...' : 'Valider l\'évaluation'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
