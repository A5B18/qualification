/**
 * Registre d'approbation — tout ce qui attend une décision, au même endroit.
 *
 * Le module `workflows` existait côté serveur sans jamais être alimenté ni
 * affiché : le tableau de bord de l'approbateur annonçait « N workflows en
 * attente » sans pouvoir en nommer un seul, et les trois modules décisionnaires
 * (rapports, mentorats, corrections d'examen) vivaient chacun dans leur écran.
 *
 * Cette page lit le registre désormais alimenté par
 * `apps.workflows.services` : un rapport, une fiche de mentorat et une
 * correction d'examen y apparaissent dans la même liste, chacun avec l'agent
 * concerné et un lien vers son écran d'origine.
 *
 * La décision est prise dans le module d'origine, pas ici : c'est lui qui porte
 * la règle métier (un rapport approuvé enregistre un avis, une correction
 * approuvée rend le score officiel). Le registre sert à voir et à retracer.
 */

import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
    GitPullRequestArrow, FileText, BookOpen, Award, Lock,
    ChevronRight, Clock, CheckCircle2, XCircle, AlertTriangle,
} from 'lucide-react'

import { workflowsApi } from '../../api'
import { useAuth } from '../../store/authContextValue'
import {
    WorkflowStatusLabels, WorkflowStatusColors,
    type ApprovalWorkflow, type WorkflowStatus, type User,
} from '../../types'
import { formatDate } from '../../utils/dates'
import { hasAnyRole } from '../../utils/roles'

/** Seuls les décideurs consultent l'ensemble du registre. */
const canDecide = (user: User | null) => hasAnyRole(user, 'APPROVER', 'UNIT_CHIEF')

const MODULE_ICONS: Record<string, typeof FileText> = {
    report: FileText,
    mentoringrecord: BookOpen,
    examsession: Award,
}

const FILTERS: { key: string; label: string }[] = [
    { key: 'SUBMITTED', label: 'En attente' },
    { key: 'APPROVED', label: 'Approuvés' },
    { key: 'REJECTED', label: 'Rejetés' },
    { key: '', label: 'Tout' },
]

const MODULES: { key: string; label: string }[] = [
    { key: '', label: 'Tous les modules' },
    { key: 'report', label: 'Rapports' },
    { key: 'mentoringrecord', label: 'Fiches de mentorat' },
    { key: 'examsession', label: "Corrections d'examen" },
]

function WorkflowRow({ entry }: { entry: ApprovalWorkflow }) {
    const Icon = MODULE_ICONS[entry.module ?? ''] ?? GitPullRequestArrow
    const status = entry.workflow_status as WorkflowStatus
    const target = entry.target

    // L'objet d'origine a pu être supprimé : la trace, elle, subsiste.
    const navigable = target && !target.deleted && target.route

    const decidedBy = entry.approver_name ?? entry.unit_chief_name
    const comment = entry.approver_comment || entry.unit_chief_comment

    const body = (
        <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3 min-w-0">
                <span className="mt-0.5 p-2 rounded-lg bg-gray-50 text-gray-500 shrink-0">
                    <Icon size={16} />
                </span>
                <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-medium text-gray-900">
                            {target?.label ?? `Objet #${entry.object_id}`}
                        </span>
                        <span className="badge bg-gray-100 text-gray-600 text-xs">
                            {entry.module_label ?? '—'}
                        </span>
                        {target?.deleted && (
                            <span className="badge bg-danger-50 text-danger-600 text-xs flex items-center gap-1">
                                <AlertTriangle size={10} /> objet supprimé
                            </span>
                        )}
                    </div>

                    <p className="text-xs text-gray-500 mt-1">
                        {target?.agent
                            ? <>Agent : {target.agent.full_name} ({target.agent.matricule})</>
                            : <>Aucun agent rattaché</>}
                    </p>

                    <p className="text-xs text-gray-400 mt-1 flex items-center gap-3 flex-wrap">
                        {entry.submitted_by_name && (
                            <span className="flex items-center gap-1">
                                <Clock size={11} />
                                Soumis par {entry.submitted_by_name}
                                {entry.submitted_at && ` le ${formatDate(entry.submitted_at)}`}
                            </span>
                        )}
                        {status === 'APPROVED' && decidedBy && (
                            <span className="flex items-center gap-1 text-success-600">
                                <CheckCircle2 size={11} />
                                Approuvé par {decidedBy}
                                {entry.approved_at && ` le ${formatDate(entry.approved_at)}`}
                            </span>
                        )}
                        {status === 'REJECTED' && decidedBy && (
                            <span className="flex items-center gap-1 text-danger-600">
                                <XCircle size={11} />
                                Rejeté par {decidedBy}
                                {entry.rejected_at && ` le ${formatDate(entry.rejected_at)}`}
                            </span>
                        )}
                    </p>

                    {comment && (
                        <p className="text-xs text-gray-600 mt-1.5 italic">« {comment} »</p>
                    )}
                </div>
            </div>

            <div className="flex items-center gap-2 shrink-0">
                <span className={`badge text-xs ${WorkflowStatusColors[status]}`}>
                    {WorkflowStatusLabels[status]}
                </span>
                {navigable && <ChevronRight size={15} className="text-gray-300" />}
            </div>
        </div>
    )

    if (navigable) {
        return (
            <Link
                to={target.route as string}
                className="card py-4 block hover:bg-gray-50 transition-colors"
                title="Ouvrir le module d'origine pour décider"
            >
                {body}
            </Link>
        )
    }
    return <div className="card py-4">{body}</div>
}

export default function WorkflowsPage() {
    const { user } = useAuth()
    const [statusFilter, setStatusFilter] = useState('SUBMITTED')
    const [moduleFilter, setModuleFilter] = useState('')

    const decider = canDecide(user)

    const { data, isLoading } = useQuery<{ count: number; results: ApprovalWorkflow[] }>({
        queryKey: ['workflows', statusFilter, moduleFilter],
        queryFn: () => workflowsApi.list({
            ...(statusFilter ? { workflow_status: statusFilter } : {}),
            ...(moduleFilter ? { module: moduleFilter } : {}),
        }).then(r => r.data),
        placeholderData: (previous) => previous,
    })

    const entries = data?.results ?? []

    const counts = useMemo(() => ({
        total: data?.count ?? 0,
    }), [data])

    return (
        <div className="space-y-5">
            <div>
                <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                    <GitPullRequestArrow size={22} className="text-asecna-600" />
                    Registre d'approbation
                </h1>
                <p className="text-sm text-gray-500 mt-1">
                    {decider
                        ? "Rapports, fiches de mentorat et corrections d'examen soumis à décision."
                        : 'Vos soumissions et leur suite.'}
                </p>
            </div>

            {!decider && (
                <div className="card flex items-start gap-2 text-sm text-gray-500">
                    <Lock size={15} className="mt-0.5 shrink-0 text-gray-400" />
                    <span>
                        Vous ne voyez ici que ce que vous avez soumis. La vue complète est
                        réservée aux chefs d'unité, approbateurs et administrateurs.
                    </span>
                </div>
            )}

            <div className="card p-4 space-y-3">
                <div className="flex gap-1 bg-gray-100 p-1 rounded-xl w-fit">
                    {FILTERS.map(({ key, label }) => (
                        <button
                            key={key || 'all'}
                            onClick={() => setStatusFilter(key)}
                            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${statusFilter === key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
                        >
                            {label}
                        </button>
                    ))}
                </div>
                <select
                    value={moduleFilter}
                    onChange={(e) => setModuleFilter(e.target.value)}
                    className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-asecna-500"
                >
                    {MODULES.map(({ key, label }) => (
                        <option key={key || 'all'} value={key}>{label}</option>
                    ))}
                </select>
            </div>

            {isLoading ? (
                <div className="flex items-center justify-center h-40">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-asecna-600" />
                </div>
            ) : entries.length === 0 ? (
                <div className="card text-center py-12 text-gray-400">
                    <GitPullRequestArrow size={40} className="mx-auto mb-2 opacity-30" />
                    <p className="text-sm">
                        {statusFilter === 'SUBMITTED'
                            ? 'Rien n’attend de décision.'
                            : 'Aucune entrée pour ce filtre.'}
                    </p>
                </div>
            ) : (
                <>
                    <p className="text-sm text-gray-500">
                        {counts.total} entrée{counts.total > 1 ? 's' : ''}
                    </p>
                    <div className="space-y-2">
                        {entries.map(entry => (
                            <WorkflowRow key={entry.id} entry={entry} />
                        ))}
                    </div>
                </>
            )}
        </div>
    )
}
