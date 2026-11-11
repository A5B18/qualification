/**
 * DashboardPage — Tableau de bord adaptatif : 7 rôles distincts.
 *
 * Rôles et vues :
 *   ADMIN        → Stats globales, graphique, toutes les alertes
 *   UNIT_CHIEF   → Approbations évals + mentorats, agents en probation, carnets ARCEP à signer
 *   APPROVER     → Rapports soumis, workflows en attente, approbations diverses
 *   EVALUATOR    → Sessions à corriger, J-14 probation, maintiens QF en retard
 *   MENTOR       → Mes agents mentorés, fiches DRAFT/SUBMITTED, objectifs
 *   INSTRUCTOR   → Mes cours (publiés/brouillons), formations et stages
 *   Agent        → Mon parcours (statut, probation, mentorat, ARCEP, dernière éval)
 */

import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../../store/authContextValue'
import {
    agentsApi, probationApi, mentoringApi, reportsApi,
    evaluationsApi, trainingApi, arcepApi,
} from '../../api'
import { Link } from 'react-router-dom'
import {
    Users, ClipboardList, BookOpen, FileText, TrendingUp,
    Award, AlertTriangle, Clock, ShieldCheck, ChevronRight,
    BookMarked, GraduationCap, CheckCircle, BookCheck,
} from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { useNow, daysUntil } from '../../utils/dates'

// ─── Utilitaires communs ──────────────────────────────────────────────────────

function StatCard({ icon: Icon, label, value, color, to }: {
    icon: any; label: string; value: number | string; color: string; to?: string
}) {
    const inner = (
        <div className="card flex items-center gap-4 hover:shadow-md transition-shadow cursor-pointer">
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${color}`}>
                <Icon size={22} className="text-white" />
            </div>
            <div>
                <div className="text-2xl font-bold text-gray-900">{value}</div>
                <div className="text-sm text-gray-500">{label}</div>
            </div>
            {to && <ChevronRight size={16} className="ml-auto text-gray-300" />}
        </div>
    )
    return to ? <Link to={to}>{inner}</Link> : inner
}

function AlertBanner({ count, label, to, color = 'border-orange-400 bg-orange-50' }: {
    count: number; label: string; to: string; color?: string
}) {
    if (count === 0) return null
    return (
        <Link to={to} className={`flex items-center gap-3 p-3 rounded-xl border-l-4 ${color} hover:opacity-80 transition-opacity`}>
            <AlertTriangle size={18} className="text-orange-600 flex-shrink-0" />
            <span className="text-sm font-medium text-gray-800">
                <span className="font-bold text-orange-700">{count}</span> {label}
            </span>
            <ChevronRight size={14} className="ml-auto text-gray-400" />
        </Link>
    )
}

function SectionCard({ title, icon: Icon, iconColor, children }: {
    title: string; icon: any; iconColor: string; children: React.ReactNode
}) {
    return (
        <div className="card">
            <h2 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <Icon size={18} className={iconColor} />
                {title}
            </h2>
            {children}
        </div>
    )
}

// ─── 1. ADMIN ────────────────────────────────────────────────────────────────

function AdminDashboard() {
    const { data: agents } = useQuery({ queryKey: ['agents-dash'], queryFn: () => agentsApi.list().then(r => r.data) })
    const { data: probations } = useQuery({ queryKey: ['probs-dash'], queryFn: () => probationApi.list().then(r => r.data) })
    const { data: mentorings } = useQuery({ queryKey: ['ments-dash'], queryFn: () => mentoringApi.list().then(r => r.data) })
    const { data: reports } = useQuery({ queryKey: ['reports-dash'], queryFn: () => reportsApi.list().then(r => r.data) })
    const { data: sessions } = useQuery({ queryKey: ['sessions-dash'], queryFn: () => evaluationsApi.sessions().then(r => r.data) })

    const profiles = agents?.results ?? []
    const probList = probations?.results ?? []
    const mentList = mentorings?.results ?? []
    const repList = reports?.results ?? []
    const sesList = sessions?.results ?? []

    const pendingEvals = sesList.filter((s: any) => s.session_status === 'PENDING_APPROVAL').length
    const pendingMent = mentList.filter((m: any) => m.mentoring_status === 'SUBMITTED').length
    const pendingReports = repList.filter((r: any) => r.report_status === 'SUBMITTED').length

    const chartData = [
        { name: 'Nouveau', value: profiles.filter((a: any) => a.status === 'NEW').length, color: '#6b7280' },
        { name: 'Probation', value: profiles.filter((a: any) => a.status === 'PROBATION').length, color: '#f59e0b' },
        { name: 'Mentorat', value: profiles.filter((a: any) => a.status === 'MENTORED').length, color: '#3b82f6' },
        { name: 'Formation', value: profiles.filter((a: any) => a.status === 'TRAINEE').length, color: '#8b5cf6' },
        { name: 'Qualifié', value: profiles.filter((a: any) => a.status === 'QUALIFIED').length, color: '#10b981' },
        { name: 'Suspendu', value: profiles.filter((a: any) => a.status === 'SUSPENDED').length, color: '#ef4444' },
    ]

    return (
        <div className="space-y-5">
            <div className="space-y-2">
                <AlertBanner count={pendingEvals} label="évaluation(s) à approuver" to="/evaluations" color="border-purple-500 bg-purple-50" />
                <AlertBanner count={pendingMent} label="mentorat(s) soumis à valider" to="/mentoring" />
                <AlertBanner count={pendingReports} label="rapport(s) soumis à traiter" to="/reports" />
            </div>

            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard icon={Users} label="Agents total" value={agents?.count ?? 0} color="bg-asecna-600" to="/agents" />
                <StatCard icon={ClipboardList} label="En probation" value={probList.filter((p: any) => p.probation_status === 'IN_PROGRESS').length} color="bg-amber-500" to="/probation" />
                <StatCard icon={BookOpen} label="En mentorat" value={mentList.filter((m: any) => m.mentoring_status !== 'COMPLETED').length} color="bg-blue-500" to="/mentoring" />
                <StatCard icon={Award} label="Évals en attente" value={pendingEvals} color="bg-purple-500" to="/evaluations" />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="card">
                    <h2 className="text-base font-semibold text-gray-900 mb-4 flex items-center gap-2">
                        <TrendingUp size={17} className="text-asecna-600" /> Répartition par statut
                    </h2>
                    <ResponsiveContainer width="100%" height={210}>
                        <BarChart data={chartData} barSize={30}>
                            <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                            <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                            <Tooltip />
                            <Bar dataKey="value" radius={[5, 5, 0, 0]}>
                                {chartData.map((e, i) => <Cell key={i} fill={e.color} />)}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
                <div className="card">
                    <h2 className="text-base font-semibold text-gray-900 mb-4">Activité en attente</h2>
                    <div className="space-y-3">
                        {[
                            { label: 'Agents qualifiés', value: profiles.filter((a: any) => a.status === 'QUALIFIED').length, color: 'bg-green-500' },
                            { label: 'Sessions à approuver', value: pendingEvals, color: 'bg-purple-500' },
                            { label: 'Mentorats soumis', value: pendingMent, color: 'bg-blue-500' },
                            { label: 'Rapports soumis', value: pendingReports, color: 'bg-orange-500' },
                        ].map(({ label, value, color }) => (
                            <div key={label} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                                <div className="flex items-center gap-3">
                                    <div className={`w-2.5 h-2.5 rounded-full ${color}`} />
                                    <span className="text-sm text-gray-600">{label}</span>
                                </div>
                                <span className="font-bold text-gray-900">{value}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    )
}

// ─── 2. CHEF D'UNITÉ ─────────────────────────────────────────────────────────

function UnitChiefDashboard() {
    const now = useNow()
    const { data: sessions } = useQuery({ queryKey: ['sess-chief'], queryFn: () => evaluationsApi.sessions().then(r => r.data) })
    const { data: mentorings } = useQuery({ queryKey: ['ment-chief'], queryFn: () => mentoringApi.list().then(r => r.data) })
    const { data: probations } = useQuery({ queryKey: ['prob-chief'], queryFn: () => probationApi.list().then(r => r.data) })
    const { data: arcepBooks } = useQuery({ queryKey: ['arcep-chief'], queryFn: () => arcepApi.books().then(r => r.data) })

    const toApproveEval = (sessions?.results ?? []).filter((s: any) => s.session_status === 'PENDING_APPROVAL')
    const toApproveMent = (mentorings?.results ?? []).filter((m: any) => m.mentoring_status === 'SUBMITTED')
    const inProbation = (probations?.results ?? []).filter((p: any) => p.probation_status === 'IN_PROGRESS')
    const books = arcepBooks?.results ?? []

    return (
        <div className="space-y-5">
            <div className="space-y-2">
                <AlertBanner count={toApproveEval.length} label="évaluation(s) à valider" to="/evaluations" color="border-purple-500 bg-purple-50" />
                <AlertBanner count={toApproveMent.length} label="fiche(s) de mentorat soumise(s)" to="/mentoring" />
            </div>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard icon={Award} label="Évals à approuver" value={toApproveEval.length} color="bg-purple-600" to="/evaluations" />
                <StatCard icon={BookOpen} label="Mentorats soumis" value={toApproveMent.length} color="bg-blue-500" to="/mentoring" />
                <StatCard icon={ClipboardList} label="En probation" value={inProbation.length} color="bg-amber-500" to="/probation" />
                <StatCard icon={BookMarked} label="Carnets ARCEP" value={books.length} color="bg-emerald-600" to="/arcep" />
            </div>

            {toApproveEval.length > 0 && (
                <SectionCard title="Corrections à approuver" icon={Award} iconColor="text-purple-600">
                    <div className="space-y-2">
                        {toApproveEval.slice(0, 5).map((s: any) => (
                            <div key={s.id} className="flex items-center justify-between p-3 rounded-lg bg-purple-50">
                                <div>
                                    <div className="text-sm font-medium text-gray-900">
                                        {s.agent_detail?.first_name} {s.agent_detail?.last_name}
                                        <span className="text-xs text-gray-500 ml-2">({s.agent_detail?.matricule})</span>
                                    </div>
                                    <div className="text-xs text-gray-500 mt-0.5">{s.exam_detail?.title} — Score provisoire : <b>{s.score ?? '?'}/100</b></div>
                                </div>
                                <Link to="/evaluations" className="text-xs text-purple-600 hover:underline flex items-center gap-1">Valider <ChevronRight size={12} /></Link>
                            </div>
                        ))}
                    </div>
                </SectionCard>
            )}

            {inProbation.length > 0 && (
                <SectionCard title="Agents en période d'essai" icon={ClipboardList} iconColor="text-amber-600">
                    <div className="space-y-2">
                        {inProbation.slice(0, 5).map((p: any) => {
                            const daysLeft = daysUntil(p.end_date, now)
                            return (
                                <div key={p.id} className="flex items-center justify-between p-3 rounded-lg bg-amber-50">
                                    <div className="text-sm font-medium text-gray-900">{p.agent_detail?.matricule ?? `Agent #${p.agent}`}</div>
                                    <span className={`text-xs font-semibold ${daysLeft < 14 ? 'text-red-600' : 'text-amber-700'}`}>
                                        {daysLeft > 0 ? `${daysLeft}j restants` : 'Délai dépassé ⚠️'}
                                    </span>
                                </div>
                            )
                        })}
                    </div>
                </SectionCard>
            )}
        </div>
    )
}

// ─── 3. APPROBATEUR ──────────────────────────────────────────────────────────

function ApproverDashboard() {
    const { data: reports } = useQuery({ queryKey: ['reports-appr'], queryFn: () => reportsApi.list().then(r => r.data) })
    const { data: mentorings } = useQuery({ queryKey: ['ments-appr'], queryFn: () => mentoringApi.list().then(r => r.data) })
    const { data: sessions } = useQuery({ queryKey: ['sess-appr'], queryFn: () => evaluationsApi.sessions().then(r => r.data) })

    const pendingReports = (reports?.results ?? []).filter((r: any) => r.report_status === 'SUBMITTED')
    const pendingMent = (mentorings?.results ?? []).filter((m: any) => m.mentoring_status === 'SUBMITTED')
    const pendingEval = (sessions?.results ?? []).filter((s: any) => s.session_status === 'PENDING_APPROVAL')

    return (
        <div className="space-y-5">
            <div className="space-y-2">
                <AlertBanner count={pendingReports.length} label="rapport(s) soumis à approuver" to="/reports" color="border-indigo-500 bg-indigo-50" />
                <AlertBanner count={pendingMent.length} label="fiche(s) de mentorat soumise(s)" to="/mentoring" />
                <AlertBanner count={pendingEval.length} label="évaluation(s) à approuver" to="/evaluations" color="border-purple-500 bg-purple-50" />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <StatCard icon={FileText} label="Rapports à approuver" value={pendingReports.length} color="bg-indigo-600" to="/reports" />
                <StatCard icon={BookOpen} label="Mentorats soumis" value={pendingMent.length} color="bg-blue-500" to="/mentoring" />
                <StatCard icon={Award} label="Évals à valider" value={pendingEval.length} color="bg-purple-500" to="/evaluations" />
            </div>

            {pendingReports.length > 0 && (
                <SectionCard title="Rapports soumis — à approuver" icon={FileText} iconColor="text-indigo-600">
                    <div className="space-y-2">
                        {pendingReports.slice(0, 6).map((r: any) => (
                            <div key={r.id} className="flex items-center justify-between p-3 rounded-lg bg-indigo-50">
                                <div>
                                    <div className="text-sm font-medium text-gray-900">{r.title}</div>
                                    <div className="text-xs text-gray-500 mt-0.5">
                                        Soumis le {r.submitted_at ? new Date(r.submitted_at).toLocaleDateString('fr-FR') : '—'}
                                    </div>
                                </div>
                                <Link to="/reports" className="text-xs text-indigo-600 hover:underline flex items-center gap-1">Examiner <ChevronRight size={12} /></Link>
                            </div>
                        ))}
                    </div>
                </SectionCard>
            )}
        </div>
    )
}

// ─── 4. ÉVALUATEUR ──────────────────────────────────────────────────────────

function EvaluatorDashboard() {
    const { data: sessions } = useQuery({ queryKey: ['sess-eval'], queryFn: () => evaluationsApi.sessions().then(r => r.data) })
    const { data: probDue } = useQuery({ queryKey: ['prob-due'], queryFn: () => probationApi.evaluationDue().then(r => r.data) })
    const { data: maintOverdue } = useQuery({ queryKey: ['maint-over'], queryFn: () => trainingApi.overdueMaintenances().then(r => r.data) })

    const submitted = (sessions?.results ?? []).filter((s: any) => s.session_status === 'SUBMITTED')
    const correcting = (sessions?.results ?? []).filter((s: any) => s.session_status === 'CORRECTING')
    const dueProb = probDue?.results ?? []
    const overdueMain = maintOverdue?.results ?? []

    return (
        <div className="space-y-5">
            <div className="space-y-2">
                <AlertBanner count={submitted.length} label="session(s) soumise(s) à corriger" to="/evaluations" color="border-yellow-400 bg-yellow-50" />
                <AlertBanner count={dueProb.length} label="probation(s) à évaluer bientôt" to="/probation" />
                <AlertBanner count={overdueMain.length} label="maintien(s) de qualification en retard" to="/training/maintenances" color="border-red-500 bg-red-50" />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <StatCard icon={Clock} label="Sessions soumises" value={submitted.length} color="bg-yellow-500" to="/evaluations" />
                <StatCard icon={Award} label="En cours de correction" value={correcting.length} color="bg-orange-500" to="/evaluations" />
                <StatCard icon={ShieldCheck} label="Maintiens en retard" value={overdueMain.length} color="bg-red-500" to="/training/maintenances" />
            </div>

            {submitted.length > 0 && (
                <SectionCard title="Sessions soumises — à corriger" icon={Award} iconColor="text-yellow-600">
                    <div className="space-y-2">
                        {submitted.slice(0, 6).map((s: any) => (
                            <div key={s.id} className="flex items-center justify-between p-3 rounded-lg bg-yellow-50">
                                <div>
                                    <div className="text-sm font-medium text-gray-900">
                                        {s.agent_detail?.first_name} {s.agent_detail?.last_name}
                                        <span className="text-xs text-gray-500 ml-2">({s.agent_detail?.matricule})</span>
                                    </div>
                                    <div className="text-xs text-gray-500 mt-0.5">{s.exam_detail?.title}</div>
                                </div>
                                <Link to="/evaluations" className="text-xs text-yellow-700 font-semibold hover:underline flex items-center gap-1">Corriger <ChevronRight size={12} /></Link>
                            </div>
                        ))}
                    </div>
                </SectionCard>
            )}

            {dueProb.length > 0 && (
                <SectionCard title="Probations à évaluer — J-14" icon={ClipboardList} iconColor="text-orange-600">
                    <div className="space-y-2">
                        {dueProb.map((p: any) => (
                            <div key={p.id} className="flex items-center justify-between p-3 rounded-lg bg-orange-50">
                                <div className="text-sm font-medium text-gray-900">{p.agent_detail?.matricule ?? `Agent #${p.agent}`}</div>
                                <span className="text-xs text-red-600 font-bold">⚠️ J-14</span>
                            </div>
                        ))}
                    </div>
                </SectionCard>
            )}
        </div>
    )
}

// ─── 5. MENTOR ───────────────────────────────────────────────────────────────

function MentorDashboard({ user }: { user: any }) {
    const { data: mentorings } = useQuery({
        queryKey: ['my-mentorings-mentor', user?.id],
        queryFn: () => mentoringApi.list().then(r => r.data),
        enabled: !!user?.id,
    })

    const allMent = mentorings?.results ?? []
    const myMentoring = allMent.filter((m: any) => m.mentor === user?.id)
    const active = myMentoring.filter((m: any) => !['COMPLETED', 'REJECTED'].includes(m.mentoring_status))
    const drafts = myMentoring.filter((m: any) => m.mentoring_status === 'DRAFT')
    const submitted = myMentoring.filter((m: any) => m.mentoring_status === 'SUBMITTED')
    const completed = myMentoring.filter((m: any) => m.mentoring_status === 'COMPLETED')

    return (
        <div className="space-y-5">
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard icon={BookOpen} label="Mes mentorats" value={myMentoring.length} color="bg-blue-600" to="/mentoring" />
                <StatCard icon={Clock} label="En cours" value={active.length} color="bg-orange-500" to="/mentoring" />
                <StatCard icon={FileText} label="Brouillons" value={drafts.length} color="bg-gray-500" to="/mentoring" />
                <StatCard icon={CheckCircle} label="Terminés" value={completed.length} color="bg-green-500" to="/mentoring" />
            </div>

            {drafts.length > 0 && (
                <SectionCard title="Fiches en brouillon — à soumettre" icon={FileText} iconColor="text-gray-500">
                    <div className="space-y-2">
                        {drafts.map((m: any) => (
                            <div key={m.id} className="flex items-center justify-between p-3 rounded-lg bg-gray-50">
                                <div>
                                    <div className="text-sm font-medium text-gray-900">
                                        Agent : {m.agent_detail?.first_name} {m.agent_detail?.last_name}
                                        <span className="text-xs text-gray-500 ml-2">({m.agent_detail?.matricule})</span>
                                    </div>
                                    <div className="text-xs text-gray-500 mt-0.5">
                                        Début : {new Date(m.start_date).toLocaleDateString('fr-FR')}
                                    </div>
                                </div>
                                <Link to="/mentoring" className="text-xs text-blue-600 hover:underline flex items-center gap-1">Soumettre <ChevronRight size={12} /></Link>
                            </div>
                        ))}
                    </div>
                </SectionCard>
            )}

            {active.filter((m: any) => m.mentoring_status === 'APPROVED').length > 0 && (
                <SectionCard title="Mes mentorats actifs" icon={BookOpen} iconColor="text-blue-600">
                    <div className="space-y-2">
                        {active.filter((m: any) => m.mentoring_status === 'APPROVED').slice(0, 5).map((m: any) => (
                            <div key={m.id} className="flex items-center justify-between p-3 rounded-lg bg-blue-50">
                                <div>
                                    <div className="text-sm font-medium text-gray-900">
                                        {m.agent_detail?.first_name} {m.agent_detail?.last_name}
                                    </div>
                                    <div className="text-xs text-gray-500 mt-0.5 line-clamp-1">{m.objectives || '—'}</div>
                                </div>
                                <span className="badge bg-green-100 text-green-700 text-xs">Approuvé ✓</span>
                            </div>
                        ))}
                    </div>
                </SectionCard>
            )}

            {submitted.length > 0 && (
                <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-xl text-yellow-800 text-sm">
                    <b>{submitted.length}</b> fiche(s) soumise(s) en attente de validation par le chef d'unité.
                </div>
            )}
        </div>
    )
}

// ─── 6. INSTRUCTEUR ──────────────────────────────────────────────────────────

function InstructorDashboard() {
    const { data: trainings } = useQuery({ queryKey: ['trainings-inst'], queryFn: () => trainingApi.trainings().then(r => r.data) })
    const { data: internships } = useQuery({ queryKey: ['internsh-inst'], queryFn: () => trainingApi.internships().then(r => r.data) })

    const allTrainings = trainings?.results ?? []
    const allInternships = internships?.results ?? []
    const activeIntern = allInternships.filter((i: any) => !i.is_passed)

    return (
        <div className="space-y-5">
            <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
                <StatCard icon={GraduationCap} label="Formations" value={allTrainings.length} color="bg-violet-600" to="/training" />
                <StatCard icon={BookCheck} label="Stages en cours" value={activeIntern.length} color="bg-orange-500" to="/training" />
                <StatCard icon={Users} label="Stagiaires actifs" value={allInternships.length} color="bg-blue-500" to="/training" />
            </div>

            {allTrainings.length > 0 && (
                <SectionCard title="Formations disponibles" icon={GraduationCap} iconColor="text-violet-600">
                    <div className="space-y-2">
                        {allTrainings.slice(0, 6).map((t: any) => (
                            <div key={t.id} className="flex items-center justify-between p-3 rounded-lg bg-violet-50">
                                <div>
                                    <div className="text-sm font-medium text-gray-900">{t.title}</div>
                                    <div className="text-xs text-gray-500 mt-0.5">
                                        {t.specialty_detail?.name ?? '—'} · Score min : {t.passing_score}%
                                    </div>
                                </div>
                                <span className={`badge text-xs ${t.training_type === 'QUALIFYING' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                                    {t.training_type === 'QUALIFYING' ? 'Qualifiante' : 'Non qualifiante'}
                                </span>
                            </div>
                        ))}
                    </div>
                </SectionCard>
            )}

            {activeIntern.length > 0 && (
                <SectionCard title="Stages en cours" icon={BookCheck} iconColor="text-orange-600">
                    <div className="space-y-2">
                        {activeIntern.slice(0, 5).map((i: any) => (
                            <div key={i.id} className="flex items-center justify-between p-3 rounded-lg bg-orange-50">
                                <div>
                                    <div className="text-sm font-medium text-gray-900">
                                        {i.agent_detail?.matricule ?? `Agent #${i.agent}`}
                                    </div>
                                    <div className="text-xs text-gray-500 mt-0.5">
                                        {i.training_detail?.title ?? '—'} · Du {new Date(i.start_date).toLocaleDateString('fr-FR')}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </SectionCard>
            )}
        </div>
    )
}

// ─── 7. AGENT standard ───────────────────────────────────────────────────────

function AgentDashboard({ user }: { user: any }) {
    const userId = user?.id

    const { data: probData } = useQuery({ queryKey: ['my-prob', userId], queryFn: () => probationApi.list().then(r => r.data), enabled: !!userId })
    const { data: mentData } = useQuery({ queryKey: ['my-ment', userId], queryFn: () => mentoringApi.list().then(r => r.data), enabled: !!userId })
    const { data: arcepData } = useQuery({ queryKey: ['my-arcep'], queryFn: () => arcepApi.books().then(r => r.data) })
    const { data: evalData } = useQuery({ queryKey: ['my-sess', userId], queryFn: () => evaluationsApi.sessions().then(r => r.data), enabled: !!userId })

    const myProbs = (probData?.results ?? []).filter((p: any) => p.agent === userId)
    const myMents = (mentData?.results ?? []).filter((m: any) => m.agent === userId)
    const myBooks = arcepData?.results ?? []
    const mySessions = evalData?.results ?? []
    const lastProb = myProbs[0]
    const lastSess = mySessions[0]

    const STATUS_COLORS: Record<string, string> = {
        NEW: 'bg-gray-100 text-gray-700', PROBATION: 'bg-yellow-100 text-yellow-700',
        MENTORED: 'bg-blue-100 text-blue-700', TRAINEE: 'bg-purple-100 text-purple-700',
        QUALIFIED: 'bg-green-100 text-green-700', SUSPENDED: 'bg-red-100 text-red-700', RETIRED: 'bg-gray-200 text-gray-500',
    }
    const STATUS_LABELS: Record<string, string> = {
        NEW: 'Nouveau', PROBATION: "Période d'essai", MENTORED: 'Mentorat',
        TRAINEE: 'Formation', QUALIFIED: 'Qualifié ✓', SUSPENDED: 'Suspendu', RETIRED: 'Retraité',
    }
    const myStatus = user?.agent_status ?? user?.status ?? 'NEW'

    return (
        <div className="space-y-5">
            {/* Ma carte de parcours */}
            <div className="card bg-gradient-to-br from-asecna-700 to-asecna-900 text-white">
                <div className="flex items-start justify-between">
                    <div>
                        <p className="text-asecna-300 text-xs uppercase tracking-wide">Mon parcours</p>
                        <h2 className="text-xl font-bold mt-1">{user?.first_name} {user?.last_name}</h2>
                        <p className="text-asecna-300 text-sm">{user?.matricule}</p>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-xs font-semibold ${STATUS_COLORS[myStatus] ?? 'bg-gray-100 text-gray-700'}`}>
                        {STATUS_LABELS[myStatus] ?? myStatus}
                    </span>
                </div>
            </div>

            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard icon={ClipboardList} label="Mes probations" value={myProbs.length} color="bg-amber-500" to="/probation" />
                <StatCard icon={BookOpen} label="Mes mentorats" value={myMents.length} color="bg-blue-500" to="/mentoring" />
                <StatCard icon={BookMarked} label="Carnets ARCEP" value={myBooks.length} color="bg-emerald-600" to="/arcep" />
                <StatCard icon={Award} label="Mes évaluations" value={mySessions.length} color="bg-purple-500" to="/evaluations" />
            </div>

            {lastProb && (
                <SectionCard title="Ma période d'essai" icon={ClipboardList} iconColor="text-amber-500">
                    <div className="flex items-center justify-between">
                        <div className="text-sm text-gray-600">
                            Tentative #{lastProb.attempt_number} · {new Date(lastProb.start_date).toLocaleDateString('fr-FR')} → {new Date(lastProb.end_date).toLocaleDateString('fr-FR')}
                            {lastProb.score != null && (
                                <div className="mt-1 font-semibold">
                                    Score : <span className={lastProb.score >= 70 ? 'text-green-600' : 'text-red-500'}>{lastProb.score}/100</span>
                                </div>
                            )}
                        </div>
                        <span className={`badge ${lastProb.probation_status === 'IN_PROGRESS' ? 'bg-blue-100 text-blue-700' : lastProb.probation_status === 'PASSED' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                            {lastProb.probation_status === 'IN_PROGRESS' ? 'En cours' : lastProb.probation_status === 'PASSED' ? 'Réussi ✓' : 'Échoué'}
                        </span>
                    </div>
                </SectionCard>
            )}

            {lastSess && (
                <SectionCard title="Ma dernière évaluation" icon={Award} iconColor="text-purple-500">
                    <div className="flex items-center justify-between">
                        <div>
                            <div className="text-sm font-medium text-gray-900">{lastSess.exam_detail?.title ?? 'Examen'}</div>
                            <div className="text-xs text-gray-500 mt-0.5">
                                {lastSess.score != null ? `Score : ${lastSess.score}/100` : 'En attente de correction'}
                            </div>
                        </div>
                        <span className={`badge text-xs ${lastSess.session_status === 'GRADED' ? 'bg-green-100 text-green-700' : lastSess.session_status === 'PENDING_APPROVAL' ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-600'}`}>
                            {lastSess.session_status === 'GRADED' ? 'Validée ✓' : lastSess.session_status === 'PENDING_APPROVAL' ? 'En attente chef' : lastSess.session_status}
                        </span>
                    </div>
                </SectionCard>
            )}
        </div>
    )
}

// ─── Logique de sélection du rôle ────────────────────────────────────────────

type RoleKey = 'admin' | 'unit_chief' | 'approver' | 'evaluator' | 'mentor' | 'instructor' | 'agent'

function detectRole(user: any): RoleKey {
    const roles: string[] = user?.roles ?? []
    if (user?.is_superuser || user?.is_admin || roles.includes('ADMIN')) return 'admin'
    if (roles.includes('UNIT_CHIEF')) return 'unit_chief'
    if (roles.includes('APPROVER')) return 'approver'
    if (roles.includes('EVALUATOR')) return 'evaluator'
    if (roles.includes('MENTOR')) return 'mentor'
    if (roles.includes('INSTRUCTOR')) return 'instructor'
    return 'agent'
}

const ROLE_META: Record<RoleKey, { label: string; color: string }> = {
    admin: { label: '🛡️ Administrateur', color: 'bg-red-100 text-red-700' },
    unit_chief: { label: '👑 Chef d\'unité', color: 'bg-asecna-100 text-asecna-700' },
    approver: { label: '✅ Approbateur', color: 'bg-indigo-100 text-indigo-700' },
    evaluator: { label: '📋 Évaluateur', color: 'bg-yellow-100 text-yellow-700' },
    mentor: { label: '🤝 Mentor', color: 'bg-blue-100 text-blue-700' },
    instructor: { label: '🎓 Instructeur', color: 'bg-violet-100 text-violet-700' },
    agent: { label: '👤 Agent', color: 'bg-gray-100 text-gray-700' },
}

// ─── Composant principal ──────────────────────────────────────────────────────

export default function DashboardPage() {
    const { user } = useAuth()
    const role = detectRole(user)
    const today = new Date().toLocaleDateString('fr-FR', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })
    const meta = ROLE_META[role]

    return (
        <div className="space-y-6">
            {/* En-tête */}
            <div className="flex items-start justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">
                        Bonjour, {user?.first_name || 'Utilisateur'} 👋
                    </h1>
                    <p className="text-gray-400 text-sm capitalize mt-0.5">{today}</p>
                </div>
                <span className={`px-3 py-1.5 rounded-full text-xs font-semibold ${meta.color}`}>
                    {meta.label}
                </span>
            </div>

            {/* Vue selon le rôle */}
            {role === 'admin' && <AdminDashboard />}
            {role === 'unit_chief' && <UnitChiefDashboard />}
            {role === 'approver' && <ApproverDashboard />}
            {role === 'evaluator' && <EvaluatorDashboard />}
            {role === 'mentor' && <MentorDashboard user={user} />}
            {role === 'instructor' && <InstructorDashboard />}
            {role === 'agent' && <AgentDashboard user={user} />}
        </div>
    )
}
