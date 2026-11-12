import { useQuery } from '@tanstack/react-query'
import { agentsApi } from '../../api'
import { useNavigate } from 'react-router-dom'
import { Users, Search, ChevronRight } from 'lucide-react'
import { useEffect, useState } from 'react'
import {
    AgentStatusLabels, AgentStatusColors,
    type AgentStatus, type User,
} from '../../types'

export default function AgentsPage() {
    const navigate = useNavigate()
    const [search, setSearch] = useState('')
    const [debounced, setDebounced] = useState('')
    const [statusFilter, setStatusFilter] = useState('')

    // La recherche part au serveur (`?search=`), qui interroge matricule, nom,
    // prénom et courriel sur l'ensemble des agents. Elle était purement locale
    // et ne portait donc que sur la page reçue : un agent absent de celle-ci
    // restait introuvable. On temporise la frappe pour ne pas lancer une
    // requête par caractère.
    useEffect(() => {
        const timer = setTimeout(() => setDebounced(search.trim()), 300)
        return () => clearTimeout(timer)
    }, [search])

    const { data, isLoading } = useQuery({
        queryKey: ['agents-profiles', debounced, statusFilter],
        queryFn: () => agentsApi.profiles({
            ...(debounced ? { search: debounced } : {}),
            ...(statusFilter ? { status: statusFilter } : {}),
        }).then(r => r.data),
        // Garde la liste précédente pendant la frappe : sans cela, chaque
        // caractère vidait le tableau le temps de la requête.
        placeholderData: (previous) => previous,
    })

    const filtered = data?.results ?? []

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                        <Users size={24} className="text-asecna-600" /> Agents
                    </h1>
                    <p className="text-gray-500 text-sm mt-1">
                        {data?.count ?? 0} agent{(data?.count ?? 0) > 1 ? 's' : ''}
                        {(debounced || statusFilter) ? ' trouvé(s)' : ' enregistré(s)'}
                    </p>
                </div>
            </div>

            {/* Barre de recherche */}
            <div className="card p-4">
                <div className="flex flex-col md:flex-row gap-3">
                    <div className="relative flex-1">
                        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                        <input
                            type="text"
                            placeholder="Rechercher par matricule, nom, prénom, courriel..."
                            value={search}
                            onChange={e => setSearch(e.target.value)}
                            className="w-full pl-9 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-asecna-500"
                        />
                    </div>
                    <select
                        value={statusFilter}
                        onChange={e => setStatusFilter(e.target.value)}
                        className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-asecna-500"
                    >
                        <option value="">Tous les statuts</option>
                        {Object.entries(AgentStatusLabels).map(([key, label]) => (
                            <option key={key} value={key}>{label}</option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Liste */}
            <div className="card p-0 overflow-hidden">
                {isLoading ? (
                    <div className="flex items-center justify-center h-48">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-asecna-600" />
                    </div>
                ) : filtered.length === 0 ? (
                    <div className="text-center py-12 text-gray-400">
                        <Users size={40} className="mx-auto mb-2 opacity-30" />
                        <p>Aucun agent trouvé</p>
                    </div>
                ) : (
                    <table className="w-full text-sm">
                        <thead className="bg-gray-50 border-b border-gray-100">
                            <tr>
                                <th className="text-left px-6 py-3 text-gray-500 font-medium">Matricule</th>
                                <th className="text-left px-6 py-3 text-gray-500 font-medium">Nom complet</th>
                                <th className="text-left px-6 py-3 text-gray-500 font-medium">Statut</th>
                                <th className="text-left px-6 py-3 text-gray-500 font-medium">Unité</th>
                                <th className="text-left px-6 py-3 text-gray-500 font-medium">Recrutement</th>
                                <th className="px-6 py-3" />
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-50">
                            {filtered.map((profile: User) => {
                                const status = profile.status as AgentStatus
                                return (
                                    <tr
                                        key={profile.id}
                                        className="hover:bg-gray-50 cursor-pointer transition-colors"
                                        onClick={() => navigate(`/agents/${profile.user}`)}
                                    >
                                        <td className="px-6 py-3.5 font-mono text-asecna-700 font-medium">
                                            {profile.user_detail?.matricule ?? `#${profile.user}`}
                                        </td>
                                        <td className="px-6 py-3.5 text-gray-900">
                                            {profile.user_detail
                                                ? `${profile.user_detail.first_name} ${profile.user_detail.last_name}`
                                                : '—'}
                                        </td>
                                        <td className="px-6 py-3.5">
                                            <span className={`badge ${AgentStatusColors[status] ?? 'bg-gray-100 text-gray-600'}`}>
                                                {AgentStatusLabels[status] ?? status}
                                            </span>
                                        </td>
                                        <td className="px-6 py-3.5 text-gray-500">
                                            {profile.unit_detail?.code ?? '—'}
                                        </td>
                                        <td className="px-6 py-3.5 text-gray-500">
                                            {profile.hire_date
                                                ? new Date(profile.hire_date).toLocaleDateString('fr-FR')
                                                : '—'}
                                        </td>
                                        <td className="px-6 py-3.5 text-gray-400">
                                            <ChevronRight size={16} />
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
