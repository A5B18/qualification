import { useQuery } from '@tanstack/react-query'
import { unitsApi, agentsApi } from '../../api'
import { Building2, Users, MapPin, ChevronDown, ChevronUp, User } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { User as AgentUser, Unit } from '../../types'

const TYPE_LABELS: Record<string, string> = {
    COM: 'Communication', NAV: 'Navigation', SURV: 'Surveillance', MET: 'Météorologie', OTHER: 'Autre',
}
const TYPE_COLORS: Record<string, string> = {
    COM: 'bg-info-100 text-info-700', NAV: 'bg-success-100 text-success-700',
    SURV: 'bg-accent-100 text-accent-700', MET: 'bg-warning-100 text-warning-700',
    OTHER: 'bg-gray-100 text-gray-600',
}
const STATUS_LABELS: Record<string, string> = {
    NEW: 'Nouveau', PROBATION: 'Probation', MENTORED: 'Mentorat',
    TRAINEE: 'Formation', QUALIFIED: 'Qualifié', SUSPENDED: 'Suspendu', RETIRED: 'Retraité',
}
const STATUS_COLORS: Record<string, string> = {
    NEW: 'bg-gray-100 text-gray-600', PROBATION: 'bg-warning-100 text-warning-700',
    MENTORED: 'bg-info-100 text-info-700', TRAINEE: 'bg-accent-100 text-accent-700',
    QUALIFIED: 'bg-success-100 text-success-700', SUSPENDED: 'bg-danger-100 text-danger-700',
    RETIRED: 'bg-gray-200 text-gray-500',
}

export default function UnitsPage() {
    const { data, isLoading } = useQuery({
        queryKey: ['units'],
        queryFn: () => unitsApi.list().then(r => r.data),
    })
    const { data: agentsData } = useQuery({
        queryKey: ['all-agents-units'],
        queryFn: () => agentsApi.list({ page_size: '200' }).then(r => r.data),
    })

    const units = data?.results ?? []
    const agents = agentsData?.results ?? []

    const totalAgents = agents.length
    const qualified = agents.filter((a: AgentUser) => a.status === 'QUALIFIED' || a.agent_profile?.status === 'QUALIFIED').length

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                    <Building2 size={24} className="text-asecna-600" /> Unités MIRE-Informatique
                </h1>
                <p className="text-gray-400 text-sm mt-0.5">{data?.count ?? 0} unités · {totalAgents} agents</p>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[
                    { label: 'Unités', value: data?.count ?? 0, color: 'text-asecna-600' },
                    { label: 'Agents total', value: totalAgents, color: 'text-info-600' },
                    { label: 'Qualifiés', value: qualified, color: 'text-success-600' },
                    { label: 'En formation', value: agents.filter((a: AgentUser) => ['PROBATION', 'MENTORED', 'TRAINEE'].includes(String(a.status ?? a.agent_profile?.status))).length, color: 'text-warning-600' },
                ].map(({ label, value, color }) => (
                    <div key={label} className="card text-center py-4">
                        <div className={`text-3xl font-bold ${color}`}>{value}</div>
                        <div className="text-sm text-gray-500 mt-1">{label}</div>
                    </div>
                ))}
            </div>

            {isLoading ? (
                <div className="flex items-center justify-center h-40">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-asecna-600" />
                </div>
            ) : units.length === 0 ? (
                <div className="card text-center py-16 text-gray-400">
                    <Building2 size={48} className="mx-auto mb-3 opacity-30" />
                    <p>Aucune unité enregistrée</p>
                </div>
            ) : (
                <div className="space-y-3">
                    {units.map((unit: Unit) => (
                        <UnitRow
                            key={unit.id}
                            unit={unit}
                            agents={agents.filter((a: AgentUser) => {
                                // Filtrer les agents appartenant à cette unité
                                return a.unit === unit.id ||
                                    a.agent_profile?.unit === unit.id ||
                                    a.unit_detail?.id === unit.id
                            })}
                        />
                    ))}
                </div>
            )}
        </div>
    )
}

function UnitRow({ unit, agents }: { unit: Unit; agents: AgentUser[] }) {
    const [expanded, setExpanded] = useState(false)

    const qualified = agents.filter((a: AgentUser) => {
        const st = a.status ?? a.agent_profile?.status
        return st === 'QUALIFIED'
    }).length

    return (
        <div className="card p-0 overflow-hidden hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between p-5 cursor-pointer" onClick={() => setExpanded(e => !e)}>
                <div className="flex items-center gap-4">
                    <div className="w-11 h-11 rounded-xl bg-asecna-100 flex items-center justify-center">
                        <Building2 size={20} className="text-asecna-700" />
                    </div>
                    <div>
                        <div className="flex items-center gap-2">
                            <span className="font-bold text-asecna-600 font-mono text-sm">{unit.code}</span>
                            <span className={`badge text-xs ${TYPE_COLORS[unit.unit_type] ?? 'bg-gray-100 text-gray-600'}`}>
                                {TYPE_LABELS[unit.unit_type] ?? unit.unit_type}
                            </span>
                            <span className={`w-2 h-2 rounded-full ${unit.is_active ? 'bg-success-400' : 'bg-gray-300'}`}
                                title={unit.is_active ? 'Actif' : 'Inactif'} />
                        </div>
                        <h3 className="font-semibold text-gray-900 mt-0.5">{unit.name}</h3>
                        {unit.description && <p className="text-xs text-gray-400 mt-0.5 line-clamp-1">{unit.description}</p>}
                    </div>
                </div>
                <div className="flex items-center gap-4">
                    <div className="text-right hidden sm:block">
                        <div className="text-sm font-semibold text-gray-700 flex items-center gap-1">
                            <Users size={13} className="text-gray-400" /> {agents.length} agent(s)
                        </div>
                        <div className="text-xs text-success-600 mt-0.5">{qualified} qualifié(s)</div>
                    </div>
                    {unit.location && (
                        <div className="text-xs text-gray-400 flex items-center gap-1 hidden md:flex">
                            <MapPin size={12} /> {unit.location}
                        </div>
                    )}
                    {expanded ? <ChevronUp size={16} className="text-gray-400" /> : <ChevronDown size={16} className="text-gray-400" />}
                </div>
            </div>

            {expanded && (
                <div className="border-t border-gray-100 p-4">
                    {agents.length === 0 ? (
                        <p className="text-sm text-gray-400 text-center py-4">Aucun agent dans cette unité</p>
                    ) : (
                        <div className="space-y-2">
                            <div className="text-xs text-gray-400 font-medium uppercase tracking-wide mb-3">
                                Agents de l'unité ({agents.length})
                            </div>
                            {agents.map((agent: AgentUser) => {
                                const status = agent.status ?? agent.agent_profile?.status ?? 'NEW'
                                return (
                                    <div key={agent.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors">
                                        <div className="flex items-center gap-3">
                                            <div className="w-8 h-8 rounded-full bg-asecna-100 flex items-center justify-center text-asecna-700 font-bold text-xs">
                                                {agent.first_name?.[0]}{agent.last_name?.[0]}
                                            </div>
                                            <div>
                                                <div className="text-sm font-medium text-gray-900">
                                                    {agent.first_name} {agent.last_name}
                                                </div>
                                                <div className="text-xs text-gray-400 font-mono">{agent.matricule}</div>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <span className={`badge text-xs ${STATUS_COLORS[status]}`}>
                                                {STATUS_LABELS[status] ?? status}
                                            </span>
                                            <Link to={`/agents/${agent.id}`}
                                                className="text-xs text-asecna-600 hover:underline flex items-center gap-1">
                                                <User size={11} /> Fiche
                                            </Link>
                                        </div>
                                    </div>
                                )
                            })}
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}
