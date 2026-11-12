import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { reportsApi, agentsApi } from '../../api'
import { useAuth } from '../../store/authContextValue'
import {
    FileText, Plus, X, CheckCircle, XCircle,
    Send, AlertTriangle,
} from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { apiErrorMessage } from '../../api/client'
import type { User, Report } from '../../types'

const STATUS_LABELS: Record<string, string> = {
    DRAFT: 'Brouillon', SUBMITTED: 'Soumis', APPROVED: 'Approuvé ✓', REJECTED: 'Rejeté',
}
const STATUS_COLORS: Record<string, string> = {
    DRAFT: 'bg-gray-100 text-gray-600',
    SUBMITTED: 'bg-info-100 text-info-700',
    APPROVED: 'bg-success-100 text-success-700',
    REJECTED: 'bg-danger-100 text-danger-700',
}
const TYPE_LABELS: Record<string, string> = {
    ASSESSMENT: 'Bilan', INCIDENT: 'Incident', PROGRESS: 'Avancement', OTHER: 'Autre',
}

function canCreate(user: User | null) {
    const r: string[] = user?.roles ?? []
    return user?.is_superuser || r.includes('ADMIN') || r.includes('UNIT_CHIEF') || r.includes('EVALUATOR')
}
function canApprove(user: User | null) {
    const r: string[] = user?.roles ?? []
    return user?.is_superuser || r.includes('ADMIN') || r.includes('APPROVER') || r.includes('UNIT_CHIEF')
}

export default function ReportsPage() {
    const { user } = useAuth()
    const qc = useQueryClient()
    const [statusFilter, setStatusFilter] = useState<string>('ALL')
    const [showCreate, setShowCreate] = useState(false)
    const [rejectId, setRejectId] = useState<number | null>(null)
    const [rejectReason, setRejectReason] = useState('')
    const [flash, setFlash] = useState<{ text: string; ok: boolean } | null>(null)
    const [form, setForm] = useState({ title: '', report_type: 'ASSESSMENT', content: '', conclusion: '', agent: '' })

    const notify = (text: string, ok = true) => {
        setFlash({ text, ok })
        setTimeout(() => setFlash(null), 4000)
    }

    const { data: reportsData, isLoading } = useQuery({
        queryKey: ['reports-all', statusFilter],
        queryFn: () => reportsApi.list(statusFilter !== 'ALL' ? { report_status: statusFilter } : {}).then(r => r.data),
    })
    const { data: agentsData } = useQuery({
        queryKey: ['agents-select'],
        queryFn: () => agentsApi.list().then(r => r.data),
        enabled: showCreate,
    })

    const reports = reportsData?.results ?? []
    const agents = agentsData?.results ?? []
    const pending = reports.filter((r: Report) => r.report_status === 'SUBMITTED').length

    const createMut = useMutation({
        mutationFn: (data: typeof form) => reportsApi.create({ ...data, agent: Number(data.agent) }),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ['reports-all'] }); setShowCreate(false); setForm({ title: '', report_type: 'ASSESSMENT', content: '', conclusion: '', agent: '' }); notify('✅ Rapport créé') },
        onError: (e: unknown) => notify(apiErrorMessage(e, '❌ Erreur création'), false),
    })
    const submitMut = useMutation({
        mutationFn: (id: number) => reportsApi.submit(id),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ['reports-all'] }); notify('📤 Rapport soumis pour approbation') },
    })
    const approveMut = useMutation({
        mutationFn: (id: number) => reportsApi.approve(id, {}),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ['reports-all'] }); notify('✅ Rapport approuvé') },
    })
    const rejectMut = useMutation({
        mutationFn: ({ id, reason }: { id: number; reason: string }) => reportsApi.reject(id, { reason }),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ['reports-all'] }); setRejectId(null); setRejectReason(''); notify('Rapport rejeté') },
    })

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                        <FileText size={24} className="text-info-600" /> Rapports
                    </h1>
                    <p className="text-gray-400 text-sm mt-0.5">{reportsData?.count ?? 0} rapports · {pending} en attente</p>
                </div>
                {canCreate(user) && (
                    <button onClick={() => setShowCreate(true)}
                        className="flex items-center gap-2 px-4 py-2 bg-info-600 hover:bg-info-700 text-white rounded-xl text-sm font-medium transition-colors">
                        <Plus size={16} /> Nouveau rapport
                    </button>
                )}
            </div>

            {flash && (
                <div className={`p-3 rounded-xl text-sm border ${flash.ok ? 'bg-success-50 border-success-200 text-success-800' : 'bg-danger-50 border-danger-200 text-danger-800'}`}>
                    {flash.text}
                </div>
            )}

            {/* KPIs */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {(['ALL', 'DRAFT', 'SUBMITTED', 'APPROVED', 'REJECTED'] as const).filter(s => s !== 'ALL').map(s => (
                    <button key={s}
                        onClick={() => setStatusFilter(s === statusFilter ? 'ALL' : s)}
                        className={`rounded-xl border p-4 text-left transition-all ${statusFilter === s ? 'ring-2 ring-info-500 ' : ''}${STATUS_COLORS[s].replace('text-', 'border-').split(' ')[0]} ${STATUS_COLORS[s]}`}>
                        <div className="text-2xl font-bold">
                            {(reportsData?.results ?? []).filter((r: Report) => r.report_status === s).length}
                        </div>
                        <div className="text-sm mt-0.5">{STATUS_LABELS[s]}</div>
                    </button>
                ))}
            </div>

            {/* Filtres rapides */}
            <div className="flex gap-2 flex-wrap">
                {['ALL', 'DRAFT', 'SUBMITTED', 'APPROVED', 'REJECTED'].map(s => (
                    <button key={s} onClick={() => setStatusFilter(s)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${statusFilter === s ? 'bg-info-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
                        {s === 'ALL' ? 'Tous' : STATUS_LABELS[s]}
                    </button>
                ))}
            </div>

            {/* Alerte rapports soumis */}
            {pending > 0 && canApprove(user) && (
                <div className="flex items-center gap-3 p-3 bg-info-50 border-l-4 border-info-500 rounded-xl text-sm">
                    <AlertTriangle size={16} className="text-info-600" />
                    <span className="text-info-800 font-medium">{pending} rapport(s) en attente d'approbation</span>
                </div>
            )}

            {/* Table */}
            <div className="card p-0 overflow-hidden">
                {isLoading ? (
                    <div className="flex items-center justify-center h-40"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-info-600" /></div>
                ) : reports.length === 0 ? (
                    <div className="text-center py-16 text-gray-400">
                        <FileText size={40} className="mx-auto mb-2 opacity-30" />
                        <p>Aucun rapport{statusFilter !== 'ALL' ? ` avec le statut "${STATUS_LABELS[statusFilter]}"` : ''}</p>
                    </div>
                ) : (
                    <table className="w-full text-sm">
                        <thead className="bg-gray-50 border-b border-gray-100">
                            <tr>
                                {['Titre', 'Type', 'Agent', 'Créé par', 'Date', 'Statut', 'Actions'].map(h => (
                                    <th key={h} className="text-left px-5 py-3 text-gray-500 font-medium text-xs uppercase tracking-wide">{h}</th>
                                ))}
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-50">
                            {reports.map((r: Report) => (
                                <tr key={r.id} className="hover:bg-gray-50">
                                    <td className="px-5 py-3.5 font-medium text-gray-900 max-w-[200px] truncate">{r.title}</td>
                                    <td className="px-5 py-3.5 text-gray-500 text-xs">{TYPE_LABELS[r.report_type] ?? r.report_type}</td>
                                    <td className="px-5 py-3.5">
                                        <Link to={`/agents/${r.agent}`} className="text-info-600 font-mono text-xs hover:underline">
                                            {r.agent_detail?.matricule ?? `#${r.agent}`}
                                        </Link>
                                    </td>
                                    <td className="px-5 py-3.5 text-gray-500 text-sm">
                                        {r.created_by_detail
                                            ? `${r.created_by_detail.first_name} ${r.created_by_detail.last_name}`
                                            : `#${r.created_by}`}
                                    </td>
                                    <td className="px-5 py-3.5 text-gray-400 text-xs">
                                        {new Date(r.created_at).toLocaleDateString('fr-FR')}
                                    </td>
                                    <td className="px-5 py-3.5">
                                        <span className={`badge text-xs ${STATUS_COLORS[r.report_status]}`}>
                                            {STATUS_LABELS[r.report_status]}
                                        </span>
                                    </td>
                                    <td className="px-5 py-3.5">
                                        <div className="flex items-center gap-2">
                                            {r.report_status === 'DRAFT' && (
                                                <button onClick={() => submitMut.mutate(r.id)}
                                                    className="text-xs flex items-center gap-1 px-2 py-1 bg-info-100 text-info-700 hover:bg-info-200 rounded-lg">
                                                    <Send size={10} /> Soumettre
                                                </button>
                                            )}
                                            {r.report_status === 'SUBMITTED' && canApprove(user) && (
                                                <>
                                                    <button onClick={() => approveMut.mutate(r.id)}
                                                        className="text-xs flex items-center gap-1 px-2 py-1 bg-success-100 text-success-700 hover:bg-success-200 rounded-lg">
                                                        <CheckCircle size={10} /> Approuver
                                                    </button>
                                                    <button onClick={() => { setRejectId(r.id); setRejectReason('') }}
                                                        className="text-xs flex items-center gap-1 px-2 py-1 bg-danger-100 text-danger-700 hover:bg-danger-200 rounded-lg">
                                                        <XCircle size={10} /> Rejeter
                                                    </button>
                                                </>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>

            {/* Modal Créer */}
            {showCreate && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
                    <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
                        <div className="flex items-center justify-between mb-5">
                            <h3 className="text-lg font-bold text-gray-900">Nouveau rapport</h3>
                            <button onClick={() => setShowCreate(false)} className="p-1 hover:bg-gray-100 rounded-lg"><X size={18} className="text-gray-400" /></button>
                        </div>
                        <form onSubmit={e => { e.preventDefault(); createMut.mutate(form) }} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Agent concerné *</label>
                                <select required value={form.agent} onChange={e => setForm(f => ({ ...f, agent: e.target.value }))}
                                    className="w-full border border-gray-200 rounded-xl p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-info-500">
                                    <option value="">— Choisir un agent —</option>
                                    {agents.map((a: User) => (
                                        <option key={a.id} value={a.id}>{a.first_name} {a.last_name} ({a.matricule})</option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Type de rapport *</label>
                                <select value={form.report_type} onChange={e => setForm(f => ({ ...f, report_type: e.target.value }))}
                                    className="w-full border border-gray-200 rounded-xl p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-info-500">
                                    {Object.entries(TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Titre *</label>
                                <input required type="text" value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                                    placeholder="Ex: Bilan périodique — T1 2024"
                                    className="w-full border border-gray-200 rounded-xl p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-info-500" />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Contenu</label>
                                <textarea value={form.content} onChange={e => setForm(f => ({ ...f, content: e.target.value }))}
                                    rows={4} placeholder="Corps du rapport..."
                                    className="w-full border border-gray-200 rounded-xl p-2.5 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-info-500" />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Conclusion</label>
                                <textarea value={form.conclusion} onChange={e => setForm(f => ({ ...f, conclusion: e.target.value }))}
                                    rows={2} placeholder="Conclusion et recommandations..."
                                    className="w-full border border-gray-200 rounded-xl p-2.5 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-info-500" />
                            </div>
                            <div className="flex gap-3 justify-end pt-2">
                                <button type="button" onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-xl">Annuler</button>
                                <button type="submit" disabled={createMut.isPending}
                                    className="px-4 py-2 text-sm font-medium text-white bg-info-600 hover:bg-info-700 rounded-xl disabled:opacity-50">
                                    {createMut.isPending ? 'Création...' : 'Créer le rapport'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Modal Rejeter */}
            {rejectId !== null && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
                    <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-md">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-bold text-gray-900">Motif de rejet</h3>
                            <button onClick={() => setRejectId(null)} className="p-1 hover:bg-gray-100 rounded-lg"><X size={18} className="text-gray-400" /></button>
                        </div>
                        <textarea value={rejectReason} onChange={e => setRejectReason(e.target.value)}
                            rows={4} placeholder="Expliquer pourquoi ce rapport est rejeté..."
                            className="w-full border border-gray-200 rounded-xl p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-danger-500" />
                        <div className="flex gap-3 mt-4 justify-end">
                            <button onClick={() => setRejectId(null)} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-xl">Annuler</button>
                            <button disabled={!rejectReason.trim() || rejectMut.isPending}
                                onClick={() => rejectMut.mutate({ id: rejectId!, reason: rejectReason })}
                                className="px-4 py-2 text-sm text-white bg-danger-600 hover:bg-danger-700 rounded-xl disabled:opacity-40">Confirmer</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
