/**
 * Gestion des comptes — réservée à l'administrateur.
 *
 * Créer un agent, lui attribuer ou lui retirer un rôle fonctionnel,
 * réinitialiser son mot de passe et désactiver son compte passaient jusqu'ici
 * obligatoirement par l'admin Django : les endpoints existaient
 * (`/auth/users/`, `assign-role`, `revoke-role`, `reset-password`) mais aucun
 * écran ne les appelait.
 */

import { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
    Users as UsersIcon, Plus, X, Search, KeyRound, ShieldPlus,
    UserMinus, Lock, Copy, AlertTriangle,
} from 'lucide-react'

import { authApi } from '../../api'
import { apiErrorMessage } from '../../api/client'
import { useAuth } from '../../store/authContextValue'
import {
    FUNCTIONAL_ROLES, FunctionalRoleLabels,
    AgentStatusLabels, AgentStatusColors,
    type AgentStatus, type User, type FunctionalRole,
} from '../../types'
import { isAdmin } from '../../utils/roles'

const EMPTY_FORM = {
    matricule: '', first_name: '', last_name: '',
    email: '', phone: '', password: '',
}

/** Format imposé par le backend (`matricule_validator`). */
const MATRICULE_PATTERN = /^ASE-\d{4}-\d{4}$/

export default function UsersPage() {
    const { user: currentUser } = useAuth()
    const qc = useQueryClient()
    const admin = isAdmin(currentUser)

    const [search, setSearch] = useState('')
    const [debounced, setDebounced] = useState('')
    const [showForm, setShowForm] = useState(false)
    const [form, setForm] = useState(EMPTY_FORM)
    const [roleDraft, setRoleDraft] = useState<Record<number, string>>({})
    const [flash, setFlash] = useState<{ text: string; ok: boolean } | null>(null)
    const [tempPassword, setTempPassword] = useState<{ matricule: string; value: string } | null>(null)

    const notify = (text: string, ok = true) => {
        setFlash({ text, ok })
        setTimeout(() => setFlash(null), 6000)
    }

    useEffect(() => {
        const timer = setTimeout(() => setDebounced(search.trim()), 300)
        return () => clearTimeout(timer)
    }, [search])

    const { data, isLoading } = useQuery<{ count: number; results: User[] }>({
        queryKey: ['users-admin', debounced],
        queryFn: () => authApi.users(debounced ? { search: debounced } : undefined).then(r => r.data),
        enabled: admin,
        placeholderData: (previous) => previous,
    })

    const users = data?.results ?? []
    const refresh = () => qc.invalidateQueries({ queryKey: ['users-admin'] })

    const createMut = useMutation({
        mutationFn: () => authApi.createUser(form),
        onSuccess: () => {
            refresh(); setShowForm(false); setForm(EMPTY_FORM)
            notify('Compte créé. Attribuez-lui un rôle si nécessaire.')
        },
        onError: (err) => notify(apiErrorMessage(err, 'Création impossible.'), false),
    })

    const assignMut = useMutation({
        mutationFn: ({ id, role }: { id: number; role: string }) =>
            authApi.assignRole(id, { role }),
        onSuccess: () => { refresh(); notify('Rôle attribué.') },
        onError: (err) => notify(apiErrorMessage(err, 'Attribution impossible.'), false),
    })

    const revokeMut = useMutation({
        mutationFn: ({ id, role }: { id: number; role: string }) => authApi.revokeRole(id, role),
        onSuccess: () => { refresh(); notify('Rôle révoqué.') },
        onError: (err) => notify(apiErrorMessage(err, 'Révocation impossible.'), false),
    })

    const resetMut = useMutation({
        mutationFn: (id: number) => authApi.resetPassword(id),
        onSuccess: (res, id) => {
            const body = res.data as {
                delivered_by_email: boolean; temp_password?: string; message: string
            }
            // Le mot de passe n'est renvoyé que si le courriel n'a pas pu
            // partir — en développement, par exemple.
            if (body.temp_password) {
                const target = users.find(u => u.id === id)
                setTempPassword({
                    matricule: target?.matricule ?? `#${id}`,
                    value: body.temp_password,
                })
            } else {
                setTempPassword(null)
            }
            notify(body.message, true)
        },
        onError: (err) => notify(apiErrorMessage(err, 'Réinitialisation impossible.'), false),
    })

    const deactivateMut = useMutation({
        mutationFn: (id: number) => authApi.deactivateUser(id),
        onSuccess: () => { refresh(); notify('Compte désactivé.') },
        onError: (err) => notify(apiErrorMessage(err, 'Désactivation impossible.'), false),
    })

    if (!admin) {
        return (
            <div className="card text-center py-12">
                <Lock size={36} className="mx-auto text-gray-300 mb-3" />
                <p className="text-gray-700 font-medium">Accès réservé à l'administrateur</p>
                <p className="text-sm text-gray-500 mt-1">
                    La gestion des comptes et des rôles n'est ouverte qu'aux administrateurs.
                </p>
            </div>
        )
    }

    const matriculeValid = MATRICULE_PATTERN.test(form.matricule)

    return (
        <div className="space-y-5">
            <div className="flex items-start justify-between gap-4 flex-wrap">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                        <UsersIcon size={22} className="text-asecna-600" /> Comptes et rôles
                    </h1>
                    <p className="text-sm text-gray-500 mt-1">
                        {data?.count ?? 0} compte(s) — création, habilitations, mot de passe.
                    </p>
                </div>
                <button
                    onClick={() => setShowForm(v => !v)}
                    className="px-4 py-2 rounded-xl text-sm font-medium bg-asecna-600 text-white hover:bg-asecna-700 flex items-center gap-2"
                >
                    {showForm ? <X size={16} /> : <Plus size={16} />}
                    {showForm ? 'Annuler' : 'Nouveau compte'}
                </button>
            </div>

            {flash && (
                <div className={`rounded-lg px-4 py-3 text-sm ${flash.ok ? 'bg-success-50 text-success-800 border border-success-200' : 'bg-danger-50 text-danger-800 border border-danger-200'}`}>
                    {flash.text}
                </div>
            )}

            {tempPassword && (
                <div className="rounded-lg px-4 py-3 bg-warning-50 border border-warning-200">
                    <p className="text-sm text-warning-900 flex items-center gap-2">
                        <AlertTriangle size={15} />
                        Mot de passe temporaire de <strong>{tempPassword.matricule}</strong> —
                        à transmettre à l'agent de la main à la main.
                    </p>
                    <div className="flex items-center gap-2 mt-2">
                        <code className="px-3 py-1.5 rounded bg-white border border-warning-200 font-mono text-sm">
                            {tempPassword.value}
                        </code>
                        <button
                            onClick={() => navigator.clipboard?.writeText(tempPassword.value)}
                            className="p-1.5 rounded hover:bg-warning-100 text-warning-700"
                            title="Copier"
                        >
                            <Copy size={14} />
                        </button>
                        <button
                            onClick={() => setTempPassword(null)}
                            className="text-xs text-warning-700 hover:underline ml-2"
                        >
                            Masquer
                        </button>
                    </div>
                </div>
            )}

            {showForm && (
                <form
                    onSubmit={(e) => { e.preventDefault(); createMut.mutate() }}
                    className="card space-y-3"
                >
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1">Matricule *</label>
                            <input
                                required value={form.matricule}
                                onChange={e => setForm(f => ({ ...f, matricule: e.target.value.toUpperCase() }))}
                                placeholder="ASE-2026-0123"
                                className="w-full border border-gray-200 rounded-lg p-2.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-asecna-500"
                            />
                            {form.matricule && !matriculeValid && (
                                <p className="text-xs text-danger-600 mt-1">Format attendu : ASE-AAAA-NNNN</p>
                            )}
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1">Prénom *</label>
                            <input
                                required value={form.first_name}
                                onChange={e => setForm(f => ({ ...f, first_name: e.target.value }))}
                                className="w-full border border-gray-200 rounded-lg p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-asecna-500"
                            />
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1">Nom *</label>
                            <input
                                required value={form.last_name}
                                onChange={e => setForm(f => ({ ...f, last_name: e.target.value }))}
                                className="w-full border border-gray-200 rounded-lg p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-asecna-500"
                            />
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1">Courriel *</label>
                            <input
                                required type="email" value={form.email}
                                onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                                className="w-full border border-gray-200 rounded-lg p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-asecna-500"
                            />
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1">Téléphone</label>
                            <input
                                value={form.phone}
                                onChange={e => setForm(f => ({ ...f, phone: e.target.value }))}
                                className="w-full border border-gray-200 rounded-lg p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-asecna-500"
                            />
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1">
                                Mot de passe initial * (8 caractères min.)
                            </label>
                            <input
                                required type="password" minLength={8} value={form.password}
                                onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                                className="w-full border border-gray-200 rounded-lg p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-asecna-500"
                            />
                        </div>
                    </div>
                    <button
                        type="submit"
                        disabled={createMut.isPending || !matriculeValid}
                        className="px-4 py-2 rounded-lg text-sm font-medium bg-asecna-600 text-white hover:bg-asecna-700 disabled:opacity-40"
                    >
                        Créer le compte
                    </button>
                </form>
            )}

            <div className="card p-3">
                <div className="relative">
                    <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                    <input
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        placeholder="Rechercher par matricule, nom, prénom, courriel…"
                        className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-asecna-500"
                    />
                </div>
            </div>

            {isLoading ? (
                <div className="flex items-center justify-center h-40">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-asecna-600" />
                </div>
            ) : users.length === 0 ? (
                <div className="card text-center py-12 text-gray-400">
                    <UsersIcon size={40} className="mx-auto mb-2 opacity-30" />
                    <p className="text-sm">Aucun compte trouvé.</p>
                </div>
            ) : (
                <div className="space-y-2">
                    {users.map(u => {
                        const roles = (u.roles ?? []) as FunctionalRole[]
                        const assignable = FUNCTIONAL_ROLES.filter(r => !roles.includes(r))
                        const status = u.status as AgentStatus | null | undefined
                        return (
                            <div key={u.id} className={`card py-4 ${u.is_active === false ? 'opacity-60' : ''}`}>
                                <div className="flex items-start justify-between gap-4 flex-wrap">
                                    <div className="min-w-0">
                                        <div className="flex items-center gap-2 flex-wrap">
                                            <span className="font-medium text-gray-900">{u.full_name}</span>
                                            <span className="font-mono text-xs text-gray-400">{u.matricule}</span>
                                            {status && (
                                                <span className={`badge text-xs ${AgentStatusColors[status]}`}>
                                                    {AgentStatusLabels[status]}
                                                </span>
                                            )}
                                            {u.is_active === false && (
                                                <span className="badge text-xs bg-danger-100 text-danger-700">Désactivé</span>
                                            )}
                                        </div>
                                        <p className="text-xs text-gray-500 mt-0.5">
                                            {u.email}
                                            {u.unit_detail && ` · ${u.unit_detail.name}`}
                                        </p>

                                        <div className="flex items-center gap-1.5 flex-wrap mt-2">
                                            {roles.length === 0 ? (
                                                <span className="text-xs text-gray-400">Aucun rôle fonctionnel</span>
                                            ) : roles.map(role => (
                                                <span
                                                    key={role}
                                                    className="badge bg-asecna-50 text-asecna-700 text-xs flex items-center gap-1"
                                                >
                                                    {FunctionalRoleLabels[role] ?? role}
                                                    <button
                                                        onClick={() => revokeMut.mutate({ id: u.id, role })}
                                                        title="Révoquer ce rôle"
                                                        className="hover:text-danger-600"
                                                    >
                                                        <X size={11} />
                                                    </button>
                                                </span>
                                            ))}
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-2 shrink-0 flex-wrap">
                                        {assignable.length > 0 && (
                                            <div className="flex items-center gap-1">
                                                <select
                                                    value={roleDraft[u.id] ?? ''}
                                                    onChange={e => setRoleDraft(d => ({ ...d, [u.id]: e.target.value }))}
                                                    className="px-2 py-1.5 border border-gray-200 rounded-lg text-xs"
                                                >
                                                    <option value="">Ajouter un rôle…</option>
                                                    {assignable.map(r => (
                                                        <option key={r} value={r}>{FunctionalRoleLabels[r]}</option>
                                                    ))}
                                                </select>
                                                <button
                                                    onClick={() => {
                                                        const role = roleDraft[u.id]
                                                        if (role) assignMut.mutate({ id: u.id, role })
                                                    }}
                                                    disabled={!roleDraft[u.id] || assignMut.isPending}
                                                    className="p-1.5 rounded-lg bg-asecna-50 text-asecna-700 hover:bg-asecna-100 disabled:opacity-40"
                                                    title="Attribuer le rôle sélectionné"
                                                >
                                                    <ShieldPlus size={14} />
                                                </button>
                                            </div>
                                        )}
                                        <button
                                            onClick={() => resetMut.mutate(u.id)}
                                            disabled={resetMut.isPending}
                                            className="px-3 py-1.5 rounded-lg text-xs bg-gray-100 text-gray-700 hover:bg-gray-200 flex items-center gap-1.5"
                                            title="Réinitialiser le mot de passe"
                                        >
                                            <KeyRound size={13} /> Mot de passe
                                        </button>
                                        {u.is_active !== false && u.id !== currentUser?.id && (
                                            <button
                                                onClick={() => deactivateMut.mutate(u.id)}
                                                disabled={deactivateMut.isPending}
                                                className="px-3 py-1.5 rounded-lg text-xs bg-white border border-danger-200 text-danger-700 hover:bg-danger-50 flex items-center gap-1.5"
                                                title="Désactiver le compte (suppression douce)"
                                            >
                                                <UserMinus size={13} /> Désactiver
                                            </button>
                                        )}
                                    </div>
                                </div>
                            </div>
                        )
                    })}
                </div>
            )}
        </div>
    )
}
