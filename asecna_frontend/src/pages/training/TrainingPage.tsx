import { useQuery, useQueryClient } from '@tanstack/react-query'
import { trainingApi, agentsApi } from '../../api'
import { useAuth } from '../../store/authContextValue'
import {
    GraduationCap, BookOpen, Plus, X, Users,
    Clock, Target, BookCheck,
} from 'lucide-react'
import { useState } from 'react'
import { apiErrorMessage } from '../../api/client'

const TYPE_LABELS: Record<string, string> = {
    QUALIFYING: 'Qualification', CONTINUING: 'Formation continue',
    REFRESHER: 'Recyclage', INITIAL: 'Formation initiale',
}
const TYPE_COLORS: Record<string, string> = {
    QUALIFYING: 'bg-asecna-100 text-asecna-700', CONTINUING: 'bg-blue-100 text-blue-700',
    REFRESHER: 'bg-orange-100 text-orange-700', INITIAL: 'bg-purple-100 text-purple-700',
}

function canCreate(user: any) {
    const r: string[] = user?.roles ?? []
    return user?.is_superuser || r.includes('ADMIN') || r.includes('INSTRUCTOR') || r.includes('UNIT_CHIEF')
}

export default function TrainingPage() {
    const { user } = useAuth()
    const qc = useQueryClient()
    const [activeTab, setActiveTab] = useState<'trainings' | 'internships'>('trainings')
    const [showCreateInternship, setShowCreateInternship] = useState(false)
    const [flash, setFlash] = useState<{ text: string; ok: boolean } | null>(null)
    const [internForm, setInternForm] = useState({ agent: '', training: '', start_date: '', end_date: '' })

    const notify = (text: string, ok = true) => {
        setFlash({ text, ok })
        setTimeout(() => setFlash(null), 4000)
    }

    const { data: specialtiesData } = useQuery({
        queryKey: ['specialties'],
        queryFn: () => trainingApi.specialties().then(r => r.data),
    })
    const { data: trainingsData, isLoading: loadingT } = useQuery({
        queryKey: ['trainings'],
        queryFn: () => trainingApi.trainings().then(r => r.data),
    })
    const { data: internshipsData, isLoading: loadingI } = useQuery({
        queryKey: ['internships'],
        queryFn: () => trainingApi.internships().then(r => r.data),
    })
    const { data: agentsData } = useQuery({
        queryKey: ['agents-select-training'],
        queryFn: () => agentsApi.list().then(r => r.data),
        enabled: showCreateInternship,
    })

    const specialties = specialtiesData?.results ?? []
    const trainings = trainingsData?.results ?? []
    const internships = internshipsData?.results ?? []
    const agents = agentsData?.results ?? []

    const activeInternships = internships.filter((i: any) => !i.is_passed)
    const passedInternships = internships.filter((i: any) => i.is_passed)

    const handleCreateInternship = async (e: React.FormEvent) => {
        e.preventDefault()
        try {
            const { default: api } = await import('../../api/client')
            await api.post('/training/internships/', {
                agent: Number(internForm.agent),
                training: Number(internForm.training),
                start_date: internForm.start_date,
                end_date: internForm.end_date,
            })
            qc.invalidateQueries({ queryKey: ['internships'] })
            setShowCreateInternship(false)
            setInternForm({ agent: '', training: '', start_date: '', end_date: '' })
            notify('✅ Stage créé avec succès')
        } catch (err: any) {
            notify(apiErrorMessage(err, '❌ Erreur'), false)
        }
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                        <GraduationCap size={24} className="text-violet-600" /> Formations & Stages
                    </h1>
                    <p className="text-gray-400 text-sm mt-0.5">
                        {trainingsData?.count ?? 0} formations · {internshipsData?.count ?? 0} stages
                    </p>
                </div>
                {canCreate(user) && (
                    <button onClick={() => setShowCreateInternship(true)}
                        className="flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-700 text-white rounded-xl text-sm font-medium transition-colors">
                        <Plus size={16} /> Inscrire à un stage
                    </button>
                )}
            </div>

            {flash && (
                <div className={`p-3 rounded-xl text-sm border ${flash.ok ? 'bg-green-50 border-green-200 text-green-800' : 'bg-red-50 border-red-200 text-red-800'}`}>
                    {flash.text}
                </div>
            )}

            {/* Spécialités */}
            {specialties.length > 0 && (
                <div className="flex flex-wrap gap-2">
                    {specialties.map((s: any) => (
                        <span key={s.id} className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-asecna-50 border border-asecna-100 text-asecna-700 rounded-full text-sm">
                            <span className="font-bold font-mono text-xs">{s.code}</span>
                            <span>{s.name}</span>
                        </span>
                    ))}
                </div>
            )}

            {/* Stats rapides */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="card text-center py-4">
                    <div className="text-2xl font-bold text-violet-600">{trainingsData?.count ?? 0}</div>
                    <div className="text-xs text-gray-500 mt-1">Formations</div>
                </div>
                <div className="card text-center py-4">
                    <div className="text-2xl font-bold text-blue-600">{activeInternships.length}</div>
                    <div className="text-xs text-gray-500 mt-1">Stages en cours</div>
                </div>
                <div className="card text-center py-4">
                    <div className="text-2xl font-bold text-green-600">{passedInternships.length}</div>
                    <div className="text-xs text-gray-500 mt-1">Stages réussis</div>
                </div>
                <div className="card text-center py-4">
                    <div className="text-2xl font-bold text-gray-600">
                        {trainings.filter((t: any) => t.training_type === 'QUALIFYING').length}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">Qualifiantes</div>
                </div>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 bg-gray-100 p-1 rounded-xl w-fit">
                {([['trainings', 'Formations', BookOpen], ['internships', 'Stages', Users]] as const).map(([key, label, Icon]) => (
                    <button key={key} onClick={() => setActiveTab(key)}
                        className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${activeTab === key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}>
                        <Icon size={15} /> {label}
                    </button>
                ))}
            </div>

            {/* Onglet Formations */}
            {activeTab === 'trainings' && (
                loadingT ? (
                    <div className="flex items-center justify-center h-40">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-violet-600" />
                    </div>
                ) : trainings.length === 0 ? (
                    <div className="card text-center py-12 text-gray-400">
                        <BookOpen size={40} className="mx-auto mb-2 opacity-30" />
                        <p>Aucune formation enregistrée</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {trainings.map((t: any) => (
                            <div key={t.id} className="card hover:shadow-md transition-shadow">
                                <div className="flex items-start justify-between mb-3">
                                    <div className="flex-1">
                                        <h3 className="font-semibold text-gray-900">{t.title}</h3>
                                        <p className="text-xs text-gray-400 mt-0.5">{t.specialty_detail?.name ?? '—'}</p>
                                    </div>
                                    <span className={`badge ml-2 text-xs ${TYPE_COLORS[t.training_type] ?? 'bg-gray-100 text-gray-600'}`}>
                                        {TYPE_LABELS[t.training_type] ?? t.training_type}
                                    </span>
                                </div>
                                {t.description && <p className="text-sm text-gray-600 mb-3 line-clamp-2">{t.description}</p>}
                                <div className="flex flex-wrap gap-3 text-xs text-gray-500 pt-3 border-t border-gray-50">
                                    <span className="flex items-center gap-1"><Clock size={11} /> {t.duration_days}j</span>
                                    <span className="flex items-center gap-1"><Target size={11} /> Seuil {t.passing_score}%</span>
                                    <span className="flex items-center gap-1"><BookCheck size={11} />
                                        {internships.filter((i: any) => i.training === t.id).length} stagiaire(s)
                                    </span>
                                    <span className={`ml-auto font-medium ${t.is_active ? 'text-green-600' : 'text-gray-400'}`}>
                                        {t.is_active ? '● Actif' : '○ Inactif'}
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                )
            )}

            {/* Onglet Stages */}
            {activeTab === 'internships' && (
                loadingI ? (
                    <div className="flex items-center justify-center h-40">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-violet-600" />
                    </div>
                ) : internships.length === 0 ? (
                    <div className="card text-center py-12 text-gray-400">
                        <Users size={40} className="mx-auto mb-2 opacity-30" />
                        <p>Aucun stage enregistré</p>
                        {canCreate(user) && (
                            <button onClick={() => setShowCreateInternship(true)}
                                className="mt-3 text-sm text-violet-600 hover:underline">
                                Inscrire un agent →
                            </button>
                        )}
                    </div>
                ) : (
                    <div className="card p-0 overflow-hidden">
                        <table className="w-full text-sm">
                            <thead className="bg-gray-50 border-b border-gray-100">
                                <tr>
                                    {['Agent', 'Formation', 'Début', 'Fin', 'Statut'].map(h => (
                                        <th key={h} className="text-left px-5 py-3 text-gray-500 font-medium text-xs uppercase tracking-wide">{h}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-50">
                                {internships.map((i: any) => (
                                    <tr key={i.id} className="hover:bg-gray-50">
                                        <td className="px-5 py-3.5">
                                            <div className="font-medium text-gray-900">{i.agent_detail?.first_name} {i.agent_detail?.last_name}</div>
                                            <div className="text-xs text-gray-400 font-mono">{i.agent_detail?.matricule}</div>
                                        </td>
                                        <td className="px-5 py-3.5 text-gray-600">{i.training_detail?.title ?? '—'}</td>
                                        <td className="px-5 py-3.5 text-gray-500 text-xs">{new Date(i.start_date).toLocaleDateString('fr-FR')}</td>
                                        <td className="px-5 py-3.5 text-gray-500 text-xs">{new Date(i.end_date).toLocaleDateString('fr-FR')}</td>
                                        <td className="px-5 py-3.5">
                                            <span className={`badge text-xs ${i.is_passed ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'}`}>
                                                {i.is_passed ? 'Réussi ✓' : 'En cours'}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )
            )}

            {/* Modal : Inscrire à un stage */}
            {showCreateInternship && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
                    <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-md">
                        <div className="flex items-center justify-between mb-5">
                            <h3 className="text-lg font-bold text-gray-900">Inscrire un agent à un stage</h3>
                            <button onClick={() => setShowCreateInternship(false)} className="p-1 hover:bg-gray-100 rounded-lg">
                                <X size={18} className="text-gray-400" />
                            </button>
                        </div>
                        <form onSubmit={handleCreateInternship} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Agent *</label>
                                <select required value={internForm.agent} onChange={e => setInternForm(f => ({ ...f, agent: e.target.value }))}
                                    className="w-full border border-gray-200 rounded-xl p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500">
                                    <option value="">— Choisir un agent —</option>
                                    {agents.map((a: any) => (
                                        <option key={a.id} value={a.id}>{a.first_name} {a.last_name} ({a.matricule})</option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Formation *</label>
                                <select required value={internForm.training} onChange={e => setInternForm(f => ({ ...f, training: e.target.value }))}
                                    className="w-full border border-gray-200 rounded-xl p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500">
                                    <option value="">— Choisir une formation —</option>
                                    {trainings.map((t: any) => (
                                        <option key={t.id} value={t.id}>{t.title}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Début *</label>
                                    <input required type="date" value={internForm.start_date}
                                        onChange={e => setInternForm(f => ({ ...f, start_date: e.target.value }))}
                                        className="w-full border border-gray-200 rounded-xl p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500" />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Fin *</label>
                                    <input required type="date" value={internForm.end_date}
                                        onChange={e => setInternForm(f => ({ ...f, end_date: e.target.value }))}
                                        className="w-full border border-gray-200 rounded-xl p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500" />
                                </div>
                            </div>
                            <div className="flex gap-3 justify-end pt-2">
                                <button type="button" onClick={() => setShowCreateInternship(false)} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-xl">Annuler</button>
                                <button type="submit"
                                    className="px-4 py-2 text-sm font-medium text-white bg-violet-600 hover:bg-violet-700 rounded-xl">
                                    Créer le stage
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    )
}
