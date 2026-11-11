import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { agentsApi, probationApi, mentoringApi, arcepApi, reportsApi } from '../../api'
import {
    ArrowLeft, User, Briefcase, ClipboardList,
    BookOpen, BookMarked, FileText, ExternalLink
} from 'lucide-react'
import {
    AgentStatusLabels, AgentStatusColors,
    ProbationStatusLabels, ProbationStatusColors,
    MentoringStatusLabels, MentoringStatusColors,
    ReportStatusLabels, ReportStatusColors, ReportTypeLabels,
    type AgentStatus, type ProbationStatus, type MentoringStatus, type ReportStatus, type ReportType
} from '../../types'
import { useNow, daysUntil } from '../../utils/dates'

type Tab = 'profil' | 'probation' | 'mentorat' | 'arcep' | 'rapports'

const TABS: { key: Tab; label: string; icon: any }[] = [
    { key: 'profil', label: 'Profil', icon: User },
    { key: 'probation', label: 'Probation', icon: ClipboardList },
    { key: 'mentorat', label: 'Mentorat', icon: BookOpen },
    { key: 'arcep', label: 'Carnet ARCEP', icon: BookMarked },
    { key: 'rapports', label: 'Rapports', icon: FileText },
]

export default function AgentDetailPage() {
    const { id } = useParams<{ id: string }>()
    const navigate = useNavigate()
    const [activeTab, setActiveTab] = useState<Tab>('profil')

    // Données utilisateur
    const { data: userData, isLoading: loadingUser } = useQuery({
        queryKey: ['agent', id],
        queryFn: () => agentsApi.get(Number(id)).then(r => r.data),
        enabled: !!id,
    })

    // Probation
    const { data: probData } = useQuery({
        queryKey: ['agent-probations', id],
        queryFn: () => probationApi.list({ agent: String(id) }).then(r => r.data),
        enabled: !!id,
    })

    // Mentorat
    const { data: mentData } = useQuery({
        queryKey: ['agent-mentoring', id],
        queryFn: () => mentoringApi.list({ agent: String(id) }).then(r => r.data),
        enabled: !!id,
    })

    // ARCEP
    const { data: arcepData } = useQuery({
        queryKey: ['agent-arcep', id],
        queryFn: () => arcepApi.books({ agent: String(id) }).then(r => r.data),
        enabled: !!id,
    })

    // Rapports
    const { data: reportsData } = useQuery({
        queryKey: ['agent-reports', id],
        queryFn: () => reportsApi.list({ agent: String(id) }).then(r => r.data),
        enabled: !!id,
    })

    if (loadingUser) return (
        <div className="flex items-center justify-center h-48">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
        </div>
    )

    if (!userData) return (
        <div className="card text-center text-gray-400 py-12">Agent introuvable.</div>
    )

    const profile = userData.agent_profile
    const status = profile?.status as AgentStatus | undefined

    return (
        <div className="space-y-6 max-w-5xl">
            {/* En-tête */}
            <div className="flex items-center gap-4">
                <button onClick={() => navigate(-1)} className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
                    <ArrowLeft size={20} className="text-gray-600" />
                </button>
                <div className="w-12 h-12 rounded-full bg-indigo-100 flex items-center justify-center">
                    <span className="text-indigo-700 font-bold text-lg">
                        {userData.first_name?.[0]}{userData.last_name?.[0]}
                    </span>
                </div>
                <div>
                    <h1 className="text-xl font-bold text-gray-900">
                        {userData.first_name} {userData.last_name}
                    </h1>
                    <p className="text-gray-500 font-mono text-sm">{userData.matricule}</p>
                </div>
                {status && (
                    <span className={`badge ml-auto ${AgentStatusColors[status]}`}>
                        {AgentStatusLabels[status]}
                    </span>
                )}
            </div>

            {/* Onglets */}
            <div className="border-b border-gray-200 flex gap-1">
                {TABS.map(({ key, label, icon: Icon }) => (
                    <button
                        key={key}
                        onClick={() => setActiveTab(key)}
                        className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${activeTab === key
                                ? 'border-indigo-600 text-indigo-600'
                                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                            }`}
                    >
                        <Icon size={15} />
                        {label}
                    </button>
                ))}
            </div>

            {/* Contenu des onglets */}
            {activeTab === 'profil' && (
                <ProfilTab user={userData} profile={profile} />
            )}
            {activeTab === 'probation' && (
                <ProbationTab probations={probData?.results ?? []} agentId={Number(id)} />
            )}
            {activeTab === 'mentorat' && (
                <MentoratTab mentorings={mentData?.results ?? []} />
            )}
            {activeTab === 'arcep' && (
                <ARCEPTab books={arcepData?.results ?? []} />
            )}
            {activeTab === 'rapports' && (
                <RapportsTab reports={reportsData?.results ?? []} />
            )}
        </div>
    )
}

// ─── Onglet Profil ────────────────────────────────────────────────────────────
function ProfilTab({ user, profile }: { user: any; profile: any }) {
    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="card space-y-4">
                <h2 className="font-semibold text-gray-900 flex items-center gap-2 text-sm uppercase tracking-wide text-gray-500">
                    <User size={14} /> Identité
                </h2>
                {[
                    { label: 'Matricule', value: user.matricule },
                    { label: 'Email', value: user.email },
                    { label: 'Prénom', value: user.first_name },
                    { label: 'Nom', value: user.last_name },
                    { label: 'Compte actif', value: user.is_active ? '✅ Oui' : '❌ Non' },
                ].map(({ label, value }) => (
                    <div key={label}>
                        <p className="text-xs text-gray-400">{label}</p>
                        <p className="text-sm font-medium text-gray-900">{value || '—'}</p>
                    </div>
                ))}
            </div>

            {profile && (
                <div className="card space-y-4">
                    <h2 className="font-semibold text-gray-900 flex items-center gap-2 text-sm uppercase tracking-wide text-gray-500">
                        <Briefcase size={14} /> Parcours
                    </h2>
                    {[
                        { label: 'Statut', value: profile.status ? AgentStatusLabels[profile.status as AgentStatus] : '—' },
                        { label: 'Unité', value: profile.unit_detail?.name ?? profile.unit_detail?.code ?? '—' },
                        { label: 'Spécialité', value: profile.specialty_detail?.name ?? '—' },
                        { label: 'Date de recrutement', value: profile.hire_date ? new Date(profile.hire_date).toLocaleDateString('fr-FR') : '—' },
                        { label: 'Qualification', value: profile.qualification_date ? new Date(profile.qualification_date).toLocaleDateString('fr-FR') : 'Pas encore qualifié' },
                    ].map(({ label, value }) => (
                        <div key={label}>
                            <p className="text-xs text-gray-400">{label}</p>
                            <p className="text-sm font-medium text-gray-900">{value}</p>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}

// ─── Onglet Probation ─────────────────────────────────────────────────────────
function ProbationTab({ probations }: { probations: any[]; agentId?: number }) {
    const now = useNow()
    if (probations.length === 0) return (
        <div className="card text-center py-10 text-gray-400">
            <ClipboardList size={36} className="mx-auto mb-2 opacity-30" />
            <p>Aucune période d'essai enregistrée pour cet agent</p>
            <Link to="/probation" className="mt-3 inline-flex items-center gap-1 text-sm text-indigo-600 hover:underline">
                <ExternalLink size={13} /> Voir toutes les probations
            </Link>
        </div>
    )
    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between">
                <h2 className="font-semibold text-gray-900">{probations.length} période(s) d'essai</h2>
                <Link to="/probation" className="text-sm text-indigo-600 hover:underline flex items-center gap-1">
                    <ExternalLink size={13} /> Vue complète
                </Link>
            </div>
            {probations.map((p: any) => {
                const status = p.probation_status as ProbationStatus
                const daysLeft = daysUntil(p.end_date, now)
                return (
                    <div key={p.id} className="card border-l-4 border-l-indigo-400 space-y-3">
                        <div className="flex items-center justify-between">
                            <span className="font-medium text-gray-900">Tentative #{p.attempt_number}</span>
                            <span className={`badge ${ProbationStatusColors[status]}`}>
                                {ProbationStatusLabels[status]}
                            </span>
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                            <div><p className="text-xs text-gray-400">Début</p><p>{new Date(p.start_date).toLocaleDateString('fr-FR')}</p></div>
                            <div><p className="text-xs text-gray-400">Fin prévue</p><p>{new Date(p.end_date).toLocaleDateString('fr-FR')}</p></div>
                            {status === 'IN_PROGRESS' && daysLeft > 0 && (
                                <div><p className="text-xs text-gray-400">Jours restants</p><p className="text-orange-600 font-semibold">{daysLeft} jours</p></div>
                            )}
                            {p.actual_end_date && (
                                <div><p className="text-xs text-gray-400">Fin effective</p><p>{new Date(p.actual_end_date).toLocaleDateString('fr-FR')}</p></div>
                            )}
                        </div>
                        {p.unit_chief_comment && (
                            <div className="bg-gray-50 rounded-lg p-3">
                                <p className="text-xs text-gray-400 mb-1">Commentaire chef d'unité</p>
                                <p className="text-sm text-gray-700">{p.unit_chief_comment}</p>
                            </div>
                        )}
                        {p.mentor_comment && (
                            <div className="bg-blue-50 rounded-lg p-3">
                                <p className="text-xs text-blue-400 mb-1">Commentaire mentor</p>
                                <p className="text-sm text-gray-700">{p.mentor_comment}</p>
                            </div>
                        )}
                    </div>
                )
            })}
        </div>
    )
}

// ─── Onglet Mentorat ──────────────────────────────────────────────────────────
function MentoratTab({ mentorings }: { mentorings: any[] }) {
    if (mentorings.length === 0) return (
        <div className="card text-center py-10 text-gray-400">
            <BookOpen size={36} className="mx-auto mb-2 opacity-30" />
            <p>Aucune fiche de mentorat pour cet agent</p>
            <Link to="/mentoring" className="mt-3 inline-flex items-center gap-1 text-sm text-indigo-600 hover:underline">
                <ExternalLink size={13} /> Voir toutes les fiches
            </Link>
        </div>
    )
    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between">
                <h2 className="font-semibold text-gray-900">{mentorings.length} fiche(s) de mentorat</h2>
                <Link to="/mentoring" className="text-sm text-indigo-600 hover:underline flex items-center gap-1">
                    <ExternalLink size={13} /> Vue complète
                </Link>
            </div>
            {mentorings.map((m: any) => {
                const status = m.mentoring_status as MentoringStatus
                return (
                    <div key={m.id} className="card border-l-4 border-l-blue-400 space-y-3">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-xs text-gray-400">Mentor</p>
                                <p className="font-medium text-gray-900">
                                    {m.mentor_detail ? `${m.mentor_detail.first_name} ${m.mentor_detail.last_name}` : `#${m.mentor}`}
                                </p>
                            </div>
                            <span className={`badge ${MentoringStatusColors[status]}`}>
                                {MentoringStatusLabels[status]}
                            </span>
                        </div>
                        <div>
                            <p className="text-xs text-gray-400 mb-1">Objectifs</p>
                            <p className="text-sm text-gray-700">{m.objectives || '—'}</p>
                        </div>
                        {m.mentor_observations && (
                            <div className="bg-blue-50 rounded-lg p-3">
                                <p className="text-xs text-blue-400 mb-1">Observations du mentor</p>
                                <p className="text-sm text-gray-700">{m.mentor_observations}</p>
                            </div>
                        )}
                        <div className="flex gap-4 text-xs text-gray-400">
                            <span>Début : {new Date(m.start_date).toLocaleDateString('fr-FR')}</span>
                            {m.end_date && <span>Fin : {new Date(m.end_date).toLocaleDateString('fr-FR')}</span>}
                        </div>
                    </div>
                )
            })}
        </div>
    )
}

// ─── Onglet ARCEP ─────────────────────────────────────────────────────────────
function ARCEPTab({ books }: { books: any[] }) {
    if (books.length === 0) return (
        <div className="card text-center py-10 text-gray-400">
            <BookMarked size={36} className="mx-auto mb-2 opacity-30" />
            <p>Aucun carnet ARCEP pour cet agent</p>
            <Link to="/arcep" className="mt-3 inline-flex items-center gap-1 text-sm text-indigo-600 hover:underline">
                <ExternalLink size={13} /> Voir tous les carnets
            </Link>
        </div>
    )
    return (
        <div className="space-y-4">
            {books.map((book: any) => (
                <ARCEPBookDetail key={book.id} book={book} />
            ))}
        </div>
    )
}

function ARCEPBookDetail({ book }: { book: any }) {
    const { data: entriesData } = useQuery({
        queryKey: ['arcep-entries-agent', book.id],
        queryFn: () => arcepApi.entries(book.id).then(r => r.data),
    })
    const entries = entriesData?.results ?? []
    const totalHours = entries.reduce((s: number, e: any) => s + Number(e.duration_hours), 0)

    return (
        <div className="card space-y-4">
            <div className="flex items-center justify-between">
                <div>
                    <span className={`badge ${book.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                        {book.is_active ? '● Actif' : '○ Inactif'}
                    </span>
                    <span className="ml-3 text-sm text-gray-500">
                        Ouvert le {new Date(book.opened_at).toLocaleDateString('fr-FR')}
                    </span>
                </div>
                <div className="text-right">
                    <p className="text-2xl font-bold text-indigo-700">{totalHours}h</p>
                    <p className="text-xs text-gray-400">total enregistré</p>
                </div>
            </div>

            {entries.length > 0 && (
                <div>
                    <p className="text-sm font-medium text-gray-700 mb-2">{entries.length} entrée(s)</p>
                    <div className="space-y-2">
                        {entries.slice(0, 5).map((e: any) => (
                            <div key={e.id} className="flex items-center justify-between bg-gray-50 rounded-lg px-3 py-2 text-sm">
                                <div>
                                    <span className="text-gray-500 text-xs mr-2">{new Date(e.entry_date).toLocaleDateString('fr-FR')}</span>
                                    <span className="text-gray-800">{e.activity}</span>
                                </div>
                                <span className="font-medium text-indigo-600">{e.duration_hours}h</span>
                            </div>
                        ))}
                        {entries.length > 5 && (
                            <p className="text-xs text-gray-400 pl-3">+ {entries.length - 5} autres entrées</p>
                        )}
                    </div>
                </div>
            )}
        </div>
    )
}

// ─── Onglet Rapports ──────────────────────────────────────────────────────────
function RapportsTab({ reports }: { reports: any[] }) {
    if (reports.length === 0) return (
        <div className="card text-center py-10 text-gray-400">
            <FileText size={36} className="mx-auto mb-2 opacity-30" />
            <p>Aucun rapport pour cet agent</p>
            <Link to="/reports" className="mt-3 inline-flex items-center gap-1 text-sm text-indigo-600 hover:underline">
                <ExternalLink size={13} /> Voir tous les rapports
            </Link>
        </div>
    )
    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between">
                <h2 className="font-semibold text-gray-900">{reports.length} rapport(s)</h2>
                <Link to="/reports" className="text-sm text-indigo-600 hover:underline flex items-center gap-1">
                    <ExternalLink size={13} /> Vue complète
                </Link>
            </div>
            {reports.map((r: any) => {
                const status = r.report_status as ReportStatus
                const type = r.report_type as ReportType
                return (
                    <div key={r.id} className="card border-l-4 border-l-purple-400 space-y-2">
                        <div className="flex items-start justify-between">
                            <div>
                                <p className="font-medium text-gray-900">{r.title}</p>
                                <p className="text-xs text-gray-400 mt-0.5">{ReportTypeLabels[type]}</p>
                            </div>
                            <span className={`badge ${ReportStatusColors[status]}`}>
                                {ReportStatusLabels[status]}
                            </span>
                        </div>
                        {r.content && (
                            <p className="text-sm text-gray-600 line-clamp-2">{r.content}</p>
                        )}
                        {r.conclusion && (
                            <div className="bg-purple-50 rounded p-2">
                                <p className="text-xs text-purple-400 mb-0.5">Conclusion</p>
                                <p className="text-sm text-gray-700">{r.conclusion}</p>
                            </div>
                        )}
                        <p className="text-xs text-gray-400">
                            Créé le {new Date(r.created_at).toLocaleDateString('fr-FR')}
                        </p>
                    </div>
                )
            })}
        </div>
    )
}
