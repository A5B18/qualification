import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { trainingApi } from '../../api'
import { ShieldCheck, AlertTriangle, Clock, CheckCircle, XCircle, MinusCircle } from 'lucide-react'
import { useState } from 'react'
import type { QualificationMaintenance } from '../../types'

const STATUS_LABELS: Record<string, string> = {
    PENDING: 'En attente',
    PASSED: 'Réussi ✓',
    FAILED: 'Échoué',
    WAIVED: 'Dispensé',
}
const STATUS_COLORS: Record<string, string> = {
    PENDING: 'bg-yellow-100 text-yellow-700',
    PASSED: 'bg-green-100 text-green-700',
    FAILED: 'bg-red-100 text-red-700',
    WAIVED: 'bg-gray-100 text-gray-600',
}
const STATUS_ICONS: Record<string, React.ReactNode> = {
    PENDING: <Clock size={14} />,
    PASSED: <CheckCircle size={14} />,
    FAILED: <XCircle size={14} />,
    WAIVED: <MinusCircle size={14} />,
}

export default function QualificationMaintenancePage() {
    const qc = useQueryClient()
    const [finalizeId, setFinalizeId] = useState<number | null>(null)
    const [score, setScore] = useState('')
    const [notes, setNotes] = useState('')
    const [actionMsg, setActionMsg] = useState<string | null>(null)

    const { data: maintData, isLoading } = useQuery({
        queryKey: ['maintenances'],
        queryFn: () => trainingApi.maintenances().then(r => r.data),
    })

    const { data: overdueData } = useQuery({
        queryKey: ['maintenances-overdue'],
        queryFn: () => trainingApi.overdueMaintenances().then(r => r.data),
    })

    const maintenances = maintData?.results ?? []
    const overdue = overdueData?.results ?? []
    const pending = maintenances.filter((m: QualificationMaintenance) => m.maintenance_status === 'PENDING')
    const passed = maintenances.filter((m: QualificationMaintenance) => m.maintenance_status === 'PASSED')

    const finalizeMut = useMutation({
        mutationFn: ({ id, score, notes }: { id: number; score: number; notes: string }) =>
            trainingApi.finalizeMaintenace(id, { score, notes }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['maintenances'] })
            qc.invalidateQueries({ queryKey: ['maintenances-overdue'] })
            setFinalizeId(null)
            setScore('')
            setNotes('')
            setActionMsg('✅ Résultat enregistré')
            setTimeout(() => setActionMsg(null), 3000)
        },
        onError: () => setActionMsg('❌ Erreur lors de la saisie du score'),
    })

    const waiveMut = useMutation({
        mutationFn: (id: number) => trainingApi.waiveMaintenance(id, { notes: 'Dispensé par le chef d\'unité.' }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['maintenances'] })
            setActionMsg('ℹ️ Agent dispensé')
            setTimeout(() => setActionMsg(null), 3000)
        },
    })

    const today = new Date()
    const getDaysUntil = (dateStr: string) =>
        Math.ceil((new Date(dateStr).getTime() - today.getTime()) / 86400000)

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                    <ShieldCheck size={24} className="text-emerald-600" /> Maintien de qualification
                </h1>
                <p className="text-gray-500 text-sm mt-1">
                    Contrôle biennal — seuil minimum <strong>70/100</strong>
                </p>
            </div>

            {actionMsg && (
                <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-blue-800 text-sm font-medium">
                    {actionMsg}
                </div>
            )}

            {/* KPIs */}
            <div className="grid grid-cols-4 gap-4">
                {[
                    { label: 'Total', value: maintData?.count ?? 0, color: 'bg-gray-50 border-gray-200 text-gray-700' },
                    { label: 'En attente', value: pending.length, color: 'bg-yellow-50 border-yellow-200 text-yellow-700' },
                    { label: 'Réussis', value: passed.length, color: 'bg-green-50 border-green-200 text-green-700' },
                    { label: 'En retard ⚠️', value: overdue.length, color: overdue.length > 0 ? 'bg-red-50 border-red-300 text-red-700' : 'bg-gray-50 border-gray-200 text-gray-500' },
                ].map(({ label, value, color }) => (
                    <div key={label} className={`rounded-xl border p-5 ${color}`}>
                        <div className="text-2xl font-bold">{value}</div>
                        <div className="text-sm mt-1">{label}</div>
                    </div>
                ))}
            </div>

            {/* Alerte : contrôles en retard */}
            {overdue.length > 0 && (
                <div className="card border-l-4 border-red-500">
                    <h2 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                        <AlertTriangle size={18} className="text-red-600" />
                        Contrôles en retard ({overdue.length})
                    </h2>
                    <div className="space-y-2">
                        {overdue.map((m: QualificationMaintenance) => (
                            <div key={m.id} className="flex items-center justify-between p-3 rounded-lg bg-red-50 border border-red-100">
                                <div>
                                    <div className="text-sm font-medium text-gray-900">
                                        {m.agent_detail?.first_name} {m.agent_detail?.last_name}
                                        <span className="ml-2 text-xs text-gray-500">({m.agent_detail?.matricule})</span>
                                    </div>
                                    <div className="text-xs text-red-600 mt-0.5">
                                        Échéance dépassée : {new Date(m.due_date).toLocaleDateString('fr-FR')}
                                        ({Math.abs(getDaysUntil(m.due_date))} jours de retard)
                                    </div>
                                </div>
                                <button
                                    onClick={() => { setFinalizeId(m.id); setScore(''); setNotes('') }}
                                    className="text-xs px-3 py-1.5 bg-red-600 text-white hover:bg-red-700 rounded-lg"
                                >
                                    Saisir le score
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Modal finalisation */}
            {finalizeId !== null && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
                    <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-md">
                        <h3 className="text-lg font-bold text-gray-900 mb-1">Saisir le résultat</h3>
                        <p className="text-sm text-gray-500 mb-4">Score ≥ 70 → Réussi | Score &lt; 70 → Échoué (agent suspendu)</p>

                        <label className="block text-sm font-medium text-gray-700 mb-1">Score (/100)</label>
                        <input
                            type="number" min="0" max="100"
                            className="w-full border border-gray-200 rounded-lg p-2.5 text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                            placeholder="Ex: 78"
                            value={score}
                            onChange={e => setScore(e.target.value)}
                        />
                        <label className="block text-sm font-medium text-gray-700 mb-1">Notes (optionnel)</label>
                        <textarea
                            className="w-full border border-gray-200 rounded-lg p-2.5 text-sm min-h-[80px] focus:outline-none focus:ring-2 focus:ring-emerald-500"
                            placeholder="Observations..."
                            value={notes}
                            onChange={e => setNotes(e.target.value)}
                        />

                        {score && Number(score) < 70 && (
                            <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded-lg text-red-700 text-xs flex items-center gap-2">
                                <AlertTriangle size={14} />
                                Score insuffisant — l'agent passera en statut SUSPENDU
                            </div>
                        )}
                        {score && Number(score) >= 70 && (
                            <div className="mt-2 p-2 bg-green-50 border border-green-200 rounded-lg text-green-700 text-xs flex items-center gap-2">
                                <CheckCircle size={14} />
                                Score suffisant — qualification maintenue
                            </div>
                        )}

                        <div className="flex gap-3 mt-4 justify-end">
                            <button
                                onClick={() => setFinalizeId(null)}
                                className="px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg"
                            >
                                Annuler
                            </button>
                            <button
                                onClick={() => finalizeId && finalizeMut.mutate({
                                    id: finalizeId,
                                    score: Number(score),
                                    notes,
                                })}
                                disabled={!score || finalizeMut.isPending}
                                className="px-4 py-2 text-sm text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg disabled:opacity-40"
                            >
                                Enregistrer
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Tableau complet */}
            <div className="card p-0 overflow-hidden">
                <div className="px-5 py-4 border-b border-gray-100">
                    <h2 className="font-semibold text-gray-900">Tous les contrôles de qualification</h2>
                </div>
                {isLoading ? (
                    <div className="flex items-center justify-center h-40">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600" />
                    </div>
                ) : maintenances.length === 0 ? (
                    <div className="text-center py-12 text-gray-400">
                        <ShieldCheck size={40} className="mx-auto mb-2 opacity-30" />
                        <p>Aucun contrôle de maintien planifié</p>
                    </div>
                ) : (
                    <table className="w-full text-sm">
                        <thead className="bg-gray-50 border-b border-gray-100">
                            <tr>
                                {['Agent', 'Échéance', 'Jours restants', 'Score', 'Statut', 'Actions'].map(h => (
                                    <th key={h} className="text-left px-6 py-3 text-gray-500 font-medium">{h}</th>
                                ))}
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-50">
                            {maintenances.map((m: QualificationMaintenance) => {
                                const daysLeft = getDaysUntil(m.due_date)
                                const st = m.maintenance_status as string
                                const isPending = st === 'PENDING'
                                return (
                                    <tr key={m.id} className="hover:bg-gray-50 transition-colors">
                                        <td className="px-6 py-3.5">
                                            <div className="font-medium text-gray-900">
                                                {m.agent_detail?.first_name} {m.agent_detail?.last_name}
                                            </div>
                                            <div className="text-xs text-gray-500">{m.agent_detail?.matricule}</div>
                                        </td>
                                        <td className="px-6 py-3.5 text-gray-600">
                                            {new Date(m.due_date).toLocaleDateString('fr-FR')}
                                        </td>
                                        <td className="px-6 py-3.5">
                                            {isPending ? (
                                                <span className={`font-semibold ${daysLeft < 0 ? 'text-red-600' : daysLeft < 30 ? 'text-orange-500' : 'text-gray-600'}`}>
                                                    {daysLeft < 0 ? `${Math.abs(daysLeft)}j retard` : `${daysLeft}j`}
                                                </span>
                                            ) : '—'}
                                        </td>
                                        <td className="px-6 py-3.5">
                                            {m.score != null
                                                ? <span className={`font-bold ${Number(m.score) >= 70 ? 'text-green-600' : 'text-red-600'}`}>{m.score}/100</span>
                                                : <span className="text-gray-300">—</span>
                                            }
                                        </td>
                                        <td className="px-6 py-3.5">
                                            <span className={`badge flex items-center gap-1 w-fit ${STATUS_COLORS[st] ?? 'bg-gray-100 text-gray-600'}`}>
                                                {STATUS_ICONS[st]}
                                                {STATUS_LABELS[st] ?? st}
                                            </span>
                                        </td>
                                        <td className="px-6 py-3.5">
                                            {isPending && (
                                                <div className="flex items-center gap-2">
                                                    <button
                                                        onClick={() => { setFinalizeId(m.id); setScore(''); setNotes('') }}
                                                        className="text-xs px-2 py-1 bg-emerald-100 text-emerald-700 hover:bg-emerald-200 rounded-lg"
                                                    >
                                                        Saisir score
                                                    </button>
                                                    <button
                                                        onClick={() => waiveMut.mutate(m.id)}
                                                        disabled={waiveMut.isPending}
                                                        className="text-xs px-2 py-1 bg-gray-100 text-gray-600 hover:bg-gray-200 rounded-lg"
                                                    >
                                                        Dispenser
                                                    </button>
                                                </div>
                                            )}
                                        </td>
                                    </tr>
                                )
                            })}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    )
}
