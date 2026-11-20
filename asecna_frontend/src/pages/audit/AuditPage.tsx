/**
 * Journal d'audit — réservé à l'administrateur.
 *
 * Les deux endpoints (`/audit/logs/`, `/audit/logins/`) existaient et étaient
 * déjà enveloppés dans `auditApi`, mais aucun écran ne les appelait : la
 * traçabilité n'était consultable que par Swagger ou par l'admin Django.
 *
 * Deux vues :
 *   • Actions   — chaque POST / PUT / PATCH / DELETE authentifié
 *   • Connexions — tentatives réussies *et* échouées
 */

import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
    ShieldAlert, Activity, LogIn, Search, CheckCircle2, XCircle, Lock,
} from 'lucide-react'

import { auditApi } from '../../api'
import { useAuth } from '../../store/authContextValue'
import type { AuditLog, LoginHistory } from '../../types'
import { isAdmin } from '../../utils/roles'

/** Couleur par méthode HTTP, pour repérer les suppressions d'un coup d'œil. */
const METHOD_COLORS: Record<string, string> = {
    POST: 'bg-success-100 text-success-700',
    PUT: 'bg-info-100 text-info-700',
    PATCH: 'bg-info-100 text-info-700',
    DELETE: 'bg-danger-100 text-danger-700',
}

function statusColor(code: number): string {
    if (code >= 500) return 'text-danger-700 font-semibold'
    if (code >= 400) return 'text-warning-700'
    return 'text-success-700'
}

function formatInstant(value: string): string {
    const d = new Date(value)
    return Number.isNaN(d.getTime()) ? '—' : d.toLocaleString('fr-FR')
}

export default function AuditPage() {
    const { user } = useAuth()
    const [tab, setTab] = useState<'actions' | 'logins'>('actions')
    const [filter, setFilter] = useState('')

    const admin = isAdmin(user)

    const { data: logsData, isLoading: loadingLogs } = useQuery<{ count: number; results: AuditLog[] }>({
        queryKey: ['audit-logs'],
        queryFn: () => auditApi.logs().then(r => r.data),
        enabled: admin && tab === 'actions',
    })

    const { data: loginsData, isLoading: loadingLogins } = useQuery<{ count: number; results: LoginHistory[] }>({
        queryKey: ['audit-logins'],
        queryFn: () => auditApi.loginHistory().then(r => r.data),
        enabled: admin && tab === 'logins',
    })

    // Le `?? []` cree un nouveau tableau a chaque rendu : on memoise d'abord
    // la liste elle-meme, sinon les useMemo qui en dependent se reevaluent
    // systematiquement.
    const logs = useMemo(() => logsData?.results ?? [], [logsData])
    const logins = useMemo(() => loginsData?.results ?? [], [loginsData])

    const filteredLogs = useMemo(() => {
        const q = filter.trim().toLowerCase()
        if (!q) return logs
        return logs.filter(l =>
            l.endpoint?.toLowerCase().includes(q)
            || l.action?.toLowerCase().includes(q)
            || String(l.status_code).includes(q),
        )
    }, [logs, filter])

    const filteredLogins = useMemo(() => {
        const q = filter.trim().toLowerCase()
        if (!q) return logins
        return logins.filter(l =>
            l.matricule_attempted?.toLowerCase().includes(q)
            || l.result?.toLowerCase().includes(q),
        )
    }, [logins, filter])

    const failedLogins = logins.filter(l => l.result === 'FAILURE').length

    // Le backend renvoie 403 à tout autre rôle ; on l'annonce plutôt que de
    // laisser l'écran se remplir d'une erreur.
    if (!admin) {
        return (
            <div className="card text-center py-12">
                <Lock size={36} className="mx-auto text-gray-300 mb-3" />
                <p className="text-gray-700 font-medium">Accès réservé à l'administrateur</p>
                <p className="text-sm text-gray-500 mt-1">
                    Le journal d'audit n'est consultable que par un compte administrateur.
                </p>
            </div>
        )
    }

    return (
        <div className="space-y-5">
            <div>
                <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                    <ShieldAlert size={22} className="text-asecna-600" /> Journal d'audit
                </h1>
                <p className="text-sm text-gray-500 mt-1">
                    Traçabilité des actions sensibles et des connexions.
                    {failedLogins > 0 && (
                        <span className="text-danger-600 ml-2">
                            {failedLogins} tentative(s) de connexion échouée(s)
                        </span>
                    )}
                </p>
            </div>

            <div className="flex gap-1 bg-gray-100 p-1 rounded-xl w-fit">
                {([
                    ['actions', 'Actions', Activity],
                    ['logins', 'Connexions', LogIn],
                ] as const).map(([key, label, Icon]) => (
                    <button
                        key={key}
                        onClick={() => setTab(key)}
                        className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${tab === key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
                    >
                        <Icon size={15} /> {label}
                    </button>
                ))}
            </div>

            <div className="card p-3">
                <div className="relative">
                    <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                    <input
                        value={filter}
                        onChange={(e) => setFilter(e.target.value)}
                        placeholder={tab === 'actions'
                            ? 'Filtrer par endpoint, méthode ou code…'
                            : 'Filtrer par matricule ou résultat…'}
                        className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-asecna-500"
                    />
                </div>
            </div>

            {tab === 'actions' ? (
                loadingLogs ? (
                    <div className="flex items-center justify-center h-40">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-asecna-600" />
                    </div>
                ) : (
                    <div className="card p-0 overflow-hidden">
                        <div className="px-5 py-3 border-b border-gray-100 text-sm text-gray-500">
                            {filteredLogs.length} action(s) sur {logsData?.count ?? 0} enregistrée(s)
                        </div>
                        {filteredLogs.length === 0 ? (
                            <p className="text-center py-10 text-gray-400 text-sm">Aucune action à afficher.</p>
                        ) : (
                            <div className="overflow-x-auto">
                                <table className="w-full text-sm">
                                    <thead className="bg-gray-50 text-xs uppercase text-gray-400">
                                        <tr>
                                            <th className="text-left px-5 py-2.5 font-medium">Horodatage</th>
                                            <th className="text-left px-5 py-2.5 font-medium">Méthode</th>
                                            <th className="text-left px-5 py-2.5 font-medium">Endpoint</th>
                                            <th className="text-left px-5 py-2.5 font-medium">Code</th>
                                            <th className="text-left px-5 py-2.5 font-medium">Adresse IP</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-gray-50">
                                        {filteredLogs.map(log => (
                                            <tr key={log.id} className="hover:bg-gray-50">
                                                <td className="px-5 py-2.5 text-gray-500 whitespace-nowrap">
                                                    {formatInstant(log.timestamp)}
                                                </td>
                                                <td className="px-5 py-2.5">
                                                    <span className={`badge text-xs ${METHOD_COLORS[log.action] ?? 'bg-gray-100 text-gray-600'}`}>
                                                        {log.action}
                                                    </span>
                                                </td>
                                                <td className="px-5 py-2.5 font-mono text-xs text-gray-700 max-w-xs truncate">
                                                    {log.endpoint}
                                                </td>
                                                <td className={`px-5 py-2.5 ${statusColor(log.status_code)}`}>
                                                    {log.status_code}
                                                </td>
                                                <td className="px-5 py-2.5 text-gray-400 font-mono text-xs">
                                                    {log.ip_address ?? '—'}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                        <p className="px-5 py-3 text-xs text-gray-400 border-t border-gray-100">
                            Les champs de mot de passe sont retirés des données journalisées.
                        </p>
                    </div>
                )
            ) : (
                loadingLogins ? (
                    <div className="flex items-center justify-center h-40">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-asecna-600" />
                    </div>
                ) : (
                    <div className="card p-0 overflow-hidden">
                        <div className="px-5 py-3 border-b border-gray-100 text-sm text-gray-500">
                            {filteredLogins.length} connexion(s) sur {loginsData?.count ?? 0} enregistrée(s)
                        </div>
                        {filteredLogins.length === 0 ? (
                            <p className="text-center py-10 text-gray-400 text-sm">Aucune connexion à afficher.</p>
                        ) : (
                            <div className="overflow-x-auto">
                                <table className="w-full text-sm">
                                    <thead className="bg-gray-50 text-xs uppercase text-gray-400">
                                        <tr>
                                            <th className="text-left px-5 py-2.5 font-medium">Horodatage</th>
                                            <th className="text-left px-5 py-2.5 font-medium">Matricule saisi</th>
                                            <th className="text-left px-5 py-2.5 font-medium">Résultat</th>
                                            <th className="text-left px-5 py-2.5 font-medium">Adresse IP</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-gray-50">
                                        {filteredLogins.map(entry => (
                                            <tr key={entry.id} className="hover:bg-gray-50">
                                                <td className="px-5 py-2.5 text-gray-500 whitespace-nowrap">
                                                    {formatInstant(entry.timestamp)}
                                                </td>
                                                <td className="px-5 py-2.5 font-mono text-xs text-gray-700">
                                                    {entry.matricule_attempted || '—'}
                                                </td>
                                                <td className="px-5 py-2.5">
                                                    {entry.result === 'SUCCESS' ? (
                                                        <span className="text-success-700 flex items-center gap-1.5 text-xs">
                                                            <CheckCircle2 size={13} /> Succès
                                                        </span>
                                                    ) : (
                                                        <span className="text-danger-700 flex items-center gap-1.5 text-xs">
                                                            <XCircle size={13} /> Échec
                                                        </span>
                                                    )}
                                                </td>
                                                <td className="px-5 py-2.5 text-gray-400 font-mono text-xs">
                                                    {entry.ip_address ?? '—'}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                )
            )}
        </div>
    )
}
