/**
 * Mon profil — coordonnées et changement de mot de passe.
 *
 * `PUT /auth/change-password/` existait sans aucun écran : un agent dont le
 * mot de passe venait d'être réinitialisé par l'administrateur n'avait aucun
 * moyen d'en choisir un nouveau depuis l'application.
 */

import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { UserCircle, KeyRound, Save, ShieldCheck, Mail, Phone, Building2 } from 'lucide-react'

import { authApi } from '../../api'
import { apiErrorMessage } from '../../api/client'
import { useAuth } from '../../store/authContextValue'
import {
    AgentStatusLabels, AgentStatusColors, FunctionalRoleLabels,
    type AgentStatus, type FunctionalRole,
} from '../../types'
import { formatDate } from '../../utils/dates'

const MIN_PASSWORD_LENGTH = 8

export default function ProfilePage() {
    const { user, updateUser, refreshProfile } = useAuth()

    const [coords, setCoords] = useState({
        email: user?.email ?? '',
        phone: (user as { phone?: string } | null)?.phone ?? '',
    })
    const [passwords, setPasswords] = useState({ old_password: '', new_password: '', confirm: '' })
    const [flash, setFlash] = useState<{ text: string; ok: boolean } | null>(null)

    const notify = (text: string, ok = true) => {
        setFlash({ text, ok })
        setTimeout(() => setFlash(null), 6000)
    }

    const coordsMut = useMutation({
        mutationFn: () => authApi.updateMe(coords),
        onSuccess: async (res) => {
            updateUser(res.data)
            await refreshProfile()
            notify('Coordonnées mises à jour.')
        },
        onError: (err) => notify(apiErrorMessage(err, 'Mise à jour impossible.'), false),
    })

    const passwordMut = useMutation({
        mutationFn: () => authApi.changePassword({
            old_password: passwords.old_password,
            new_password: passwords.new_password,
        }),
        onSuccess: () => {
            setPasswords({ old_password: '', new_password: '', confirm: '' })
            notify('Mot de passe modifié. Il sera demandé à la prochaine connexion.')
        },
        onError: (err) => notify(apiErrorMessage(err, 'Changement impossible.'), false),
    })

    // La confirmation est vérifiée ici : le backend ne reçoit que
    // `old_password` et `new_password`, il ne peut donc pas détecter une
    // faute de frappe sur la saisie répétée.
    const mismatch =
        passwords.confirm.length > 0 && passwords.new_password !== passwords.confirm
    const tooShort =
        passwords.new_password.length > 0 && passwords.new_password.length < MIN_PASSWORD_LENGTH
    const canSubmitPassword =
        passwords.old_password.length > 0
        && passwords.new_password.length >= MIN_PASSWORD_LENGTH
        && passwords.new_password === passwords.confirm

    const status = user?.status as AgentStatus | null | undefined
    const roles = (user?.roles ?? []) as FunctionalRole[]

    return (
        <div className="space-y-5 max-w-3xl">
            <div>
                <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                    <UserCircle size={22} className="text-asecna-600" /> Mon profil
                </h1>
                <p className="text-sm text-gray-500 mt-1">
                    {user?.full_name} · <span className="font-mono">{user?.matricule}</span>
                </p>
            </div>

            {flash && (
                <div className={`rounded-lg px-4 py-3 text-sm ${flash.ok ? 'bg-green-50 text-green-800 border border-green-200' : 'bg-red-50 text-red-800 border border-red-200'}`}>
                    {flash.text}
                </div>
            )}

            {/* Parcours — lecture seule : seul un administrateur le fait évoluer */}
            <div className="card">
                <h2 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                    <ShieldCheck size={16} className="text-asecna-600" /> Mon parcours
                </h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                    <div>
                        <p className="text-xs uppercase tracking-wide text-gray-400 mb-1">Statut</p>
                        {status ? (
                            <span className={`badge ${AgentStatusColors[status]}`}>
                                {AgentStatusLabels[status]}
                            </span>
                        ) : <span className="text-gray-400">—</span>}
                    </div>
                    <div>
                        <p className="text-xs uppercase tracking-wide text-gray-400 mb-1">Unité</p>
                        <p className="text-gray-800 flex items-center gap-1.5">
                            <Building2 size={13} className="text-gray-400" />
                            {user?.unit_detail?.name ?? '—'}
                        </p>
                    </div>
                    <div>
                        <p className="text-xs uppercase tracking-wide text-gray-400 mb-1">Recrutement</p>
                        <p className="text-gray-800">{formatDate(user?.hire_date)}</p>
                    </div>
                    <div>
                        <p className="text-xs uppercase tracking-wide text-gray-400 mb-1">Qualification</p>
                        <p className="text-gray-800">{formatDate(user?.qualification_date)}</p>
                    </div>
                </div>
                <div className="mt-4 pt-3 border-t border-gray-50">
                    <p className="text-xs uppercase tracking-wide text-gray-400 mb-2">Rôles fonctionnels</p>
                    <div className="flex flex-wrap gap-1.5">
                        {roles.length === 0 ? (
                            <span className="text-sm text-gray-400">Agent (aucun rôle d'encadrement)</span>
                        ) : roles.map(role => (
                            <span key={role} className="badge bg-asecna-50 text-asecna-700">
                                {FunctionalRoleLabels[role] ?? role}
                            </span>
                        ))}
                    </div>
                </div>
            </div>

            {/* Coordonnées */}
            <form
                onSubmit={(e) => { e.preventDefault(); coordsMut.mutate() }}
                className="card space-y-3"
            >
                <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                    <Mail size={16} className="text-asecna-600" /> Mes coordonnées
                </h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Courriel</label>
                        <input
                            type="email" value={coords.email}
                            onChange={e => setCoords(c => ({ ...c, email: e.target.value }))}
                            className="w-full border border-gray-200 rounded-lg p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-asecna-500"
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">
                            <Phone size={11} className="inline mr-1" />Téléphone
                        </label>
                        <input
                            value={coords.phone}
                            onChange={e => setCoords(c => ({ ...c, phone: e.target.value }))}
                            className="w-full border border-gray-200 rounded-lg p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-asecna-500"
                        />
                    </div>
                </div>
                <button
                    type="submit"
                    disabled={coordsMut.isPending}
                    className="px-4 py-2 rounded-lg text-sm font-medium bg-asecna-600 text-white hover:bg-asecna-700 disabled:opacity-40 flex items-center gap-1.5"
                >
                    <Save size={14} /> Enregistrer
                </button>
            </form>

            {/* Mot de passe */}
            <form
                onSubmit={(e) => { e.preventDefault(); passwordMut.mutate() }}
                className="card space-y-3"
            >
                <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                    <KeyRound size={16} className="text-asecna-600" /> Changer mon mot de passe
                </h2>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Mot de passe actuel</label>
                        <input
                            type="password" value={passwords.old_password}
                            onChange={e => setPasswords(p => ({ ...p, old_password: e.target.value }))}
                            className="w-full border border-gray-200 rounded-lg p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-asecna-500"
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">
                            Nouveau ({MIN_PASSWORD_LENGTH} caractères min.)
                        </label>
                        <input
                            type="password" value={passwords.new_password}
                            onChange={e => setPasswords(p => ({ ...p, new_password: e.target.value }))}
                            className="w-full border border-gray-200 rounded-lg p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-asecna-500"
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Confirmation</label>
                        <input
                            type="password" value={passwords.confirm}
                            onChange={e => setPasswords(p => ({ ...p, confirm: e.target.value }))}
                            className="w-full border border-gray-200 rounded-lg p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-asecna-500"
                        />
                    </div>
                </div>
                {tooShort && (
                    <p className="text-xs text-red-600">
                        Le nouveau mot de passe doit faire au moins {MIN_PASSWORD_LENGTH} caractères.
                    </p>
                )}
                {mismatch && (
                    <p className="text-xs text-red-600">La confirmation ne correspond pas.</p>
                )}
                <button
                    type="submit"
                    disabled={!canSubmitPassword || passwordMut.isPending}
                    className="px-4 py-2 rounded-lg text-sm font-medium bg-asecna-600 text-white hover:bg-asecna-700 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                    Changer le mot de passe
                </button>
            </form>
        </div>
    )
}
