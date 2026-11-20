/**
 * Blocs communs aux deux vues du carnet ARCEP.
 *
 * Le carnet se lit a deux endroits : l'ecran « Carnets ARCEP » et l'onglet
 * « Carnet ARCEP » de la fiche agent. Les deux doivent montrer la meme chose,
 * d'ou ce module partage : une seule definition de l'en-tete d'identite et du
 * tableau des echeances, qui ne peuvent donc plus diverger.
 */

import {
    BookMarked, Calendar, Clock, PenLine,
    IdCard, Briefcase, Building2, Mail, Phone, Award,
    CalendarClock, AlertTriangle, ShieldCheck,
} from 'lucide-react'

import {
    AgentStatusColors, QualificationStatusColors, QualificationStatusLabels,
    FunctionalRoleLabels,
    type ARCEPBook, type ARCEPAgentIdentity, type ARCEPQualification,
    type ARCEPQualificationsSummary, type AgentStatus, type FunctionalRole,
} from '../types'
import { formatDate } from '../utils/dates'

/** Teintes de la pastille d'alerte des echeances. */
const ALERT_TONES: Record<string, string> = {
    OK: 'bg-success-100 text-success-700',
    WARNING: 'bg-warning-100 text-warning-700',
    CRITICAL: 'bg-danger-100 text-danger-700',
}

/** Resume d'une ligne d'echeance, pour la pastille du carnet replie. */
function alertText(summary?: ARCEPQualificationsSummary): string | null {
    if (!summary || summary.total === 0) return null
    if (summary.expired > 0) {
        return `${summary.expired} échéance${summary.expired > 1 ? 's' : ''} dépassée${summary.expired > 1 ? 's' : ''}`
    }
    if (summary.expiring_soon > 0) {
        return `${summary.expiring_soon} échéance${summary.expiring_soon > 1 ? 's' : ''} proche${summary.expiring_soon > 1 ? 's' : ''}`
    }
    return 'Qualifications à jour'
}

/** Pastille d'alerte des echeances, avec l'icone qui va avec le niveau. */
export function QualificationAlertBadge({ summary }: {
    summary?: ARCEPQualificationsSummary
}) {
    const label = alertText(summary)
    if (!label) return null
    const level = summary?.alert_level ?? 'OK'
    return (
        <span className={`badge text-xs flex items-center gap-1 ${ALERT_TONES[level]}`}
            title={`Fenêtre d'alerte : ${summary?.warning_window_days ?? 90} jours`}>
            {level === 'OK' ? <ShieldCheck size={10} /> : <AlertTriangle size={10} />}
            {label}
        </span>
    )
}

// ─── Premiere page du carnet : identite du titulaire ─────────────────────────

export function SectionTitle({ icon, label }: { icon: React.ReactNode; label: string }) {
    return (
        <div className="text-xs text-gray-400 font-medium uppercase tracking-wide mb-3 flex items-center gap-1.5">
            {icon} {label}
        </div>
    )
}

function Field({ label, value, icon }: {
    label: string; value: React.ReactNode; icon?: React.ReactNode
}) {
    return (
        <div>
            <div className="text-xs text-gray-400 flex items-center gap-1">{icon} {label}</div>
            <div className="text-sm text-gray-900 mt-0.5 break-words">{value || '—'}</div>
        </div>
    )
}

export function AgentIdentityCard({ identity, book }: {
    identity: ARCEPAgentIdentity | null; book: ARCEPBook
}) {
    if (!identity) {
        // Carnet servi par une version anterieure de l'API : on garde le
        // minimum plutot qu'un bloc vide.
        return (
            <div className="rounded-xl border border-gray-100 bg-gray-50 p-4 text-sm text-gray-500">
                Identité du titulaire indisponible pour ce carnet.
            </div>
        )
    }

    const status = identity.career_status as AgentStatus | null

    return (
        <div className="rounded-xl border border-asecna-100 bg-asecna-50/50 p-4">
            <SectionTitle icon={<IdCard size={12} />} label="Titulaire du carnet" />

            <div className="flex items-start gap-4">
                {identity.photo ? (
                    <img src={identity.photo} alt=""
                        className="w-14 h-14 rounded-xl object-cover border border-white shadow-sm" />
                ) : (
                    <div className="w-14 h-14 rounded-xl bg-asecna-100 flex items-center justify-center text-asecna-700 font-semibold">
                        {identity.first_name.charAt(0)}{identity.last_name.charAt(0)}
                    </div>
                )}
                <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-semibold text-gray-900">
                            {identity.last_name.toUpperCase()} {identity.first_name}
                        </span>
                        {status && (
                            <span className={`badge text-xs ${AgentStatusColors[status]}`}>
                                {identity.career_status_label}
                            </span>
                        )}
                    </div>
                    <div className="text-xs text-gray-500 font-mono mt-0.5">{identity.matricule}</div>
                    {identity.roles.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
                            {identity.roles.map(role => (
                                <span key={role} className="badge text-xs bg-white text-gray-600 border border-gray-200">
                                    {FunctionalRoleLabels[role as FunctionalRole] ?? role}
                                </span>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            <div className="grid grid-cols-2 lg:grid-cols-4 gap-x-4 gap-y-3 mt-4 pt-4 border-t border-asecna-100">
                <Field label="Profession" icon={<Briefcase size={10} />}
                    value={identity.profession
                        ? `${identity.profession}${identity.profession_code ? ` (${identity.profession_code})` : ''}`
                        : null} />
                <Field label="Unité d'affectation" icon={<Building2 size={10} />}
                    value={identity.unit
                        ? `${identity.unit.code} — ${identity.unit.name}`
                        : null} />
                <Field label="Localisation" value={identity.unit
                    ? [identity.unit.location, identity.unit.country].filter(Boolean).join(', ')
                    : null} />
                <Field label="Type d'unité" value={identity.unit?.unit_type_label} />
                <Field label="Recrutement" icon={<Calendar size={10} />}
                    value={formatDate(identity.hire_date)} />
                <Field label="Qualification" icon={<Award size={10} />}
                    value={formatDate(identity.qualification_date)} />
                <Field label="Ancienneté"
                    value={identity.seniority_years === null
                        ? null
                        : `${identity.seniority_years} an${identity.seniority_years > 1 ? 's' : ''}`} />
                <Field label="Carnet ouvert le" icon={<BookMarked size={10} />}
                    value={formatDate(book.opened_at)} />
                <Field label="Courriel" icon={<Mail size={10} />} value={identity.email} />
                <Field label="Téléphone" icon={<Phone size={10} />} value={identity.phone} />
                <Field label="Dernier visa du chef" icon={<PenLine size={10} />}
                    value={book.last_signed_on
                        ? `jusqu'au ${formatDate(book.last_signed_on)}`
                        : 'jamais visé'} />
                <Field label="Heures cumulées" icon={<Clock size={10} />}
                    value={`${book.total_hours ?? 0}h sur ${book.entries_count ?? 0} entrée(s)`} />
            </div>
        </div>
    )
}

// ─── Deuxieme page : qualifications et echeances ──────────────────────────────

export function QualificationsPanel({ items, summary }: {
    items: ARCEPQualification[]; summary?: ARCEPQualificationsSummary
}) {
    return (
        <div>
            <SectionTitle icon={<Award size={12} />} label="Qualifications et échéances" />

            {summary && summary.total > 0 && (
                <div className="flex flex-wrap items-center gap-2 mb-3">
                    <span className={`badge text-xs ${ALERT_TONES[summary.alert_level]}`}>
                        {summary.valid} valide(s) · {summary.expiring_soon} à surveiller · {summary.expired} dépassée(s)
                    </span>
                    {summary.next_due_date && (
                        <span className="text-xs text-gray-500 flex items-center gap-1">
                            <CalendarClock size={11} />
                            Prochaine échéance : {formatDate(summary.next_due_date)}
                            {summary.next_due_in_days !== null && ` (J+${summary.next_due_in_days})`}
                            {summary.next_due_label && ` — ${summary.next_due_label}`}
                        </span>
                    )}
                </div>
            )}

            {items.length === 0 ? (
                <p className="text-sm text-gray-400 py-3">
                    Aucune qualification enregistrée pour cet agent.
                </p>
            ) : (
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="text-xs text-gray-400 uppercase tracking-wide text-left">
                                <th className="py-2 pr-3 font-medium">Qualification</th>
                                <th className="py-2 pr-3 font-medium">Origine</th>
                                <th className="py-2 pr-3 font-medium">Obtenue le</th>
                                <th className="py-2 pr-3 font-medium">Échéance</th>
                                <th className="py-2 pr-3 font-medium">État</th>
                            </tr>
                        </thead>
                        <tbody>
                            {items.map((item, i) => (
                                <tr key={`${item.kind}-${item.label}-${i}`}
                                    className="border-t border-gray-100 align-top">
                                    <td className="py-2 pr-3">
                                        <div className="text-gray-900">{item.label}</div>
                                        {item.issuer && (
                                            <div className="text-xs text-gray-400">{item.issuer}</div>
                                        )}
                                        {item.score && (
                                            <div className="text-xs text-gray-500">Score : {item.score}/100</div>
                                        )}
                                    </td>
                                    <td className="py-2 pr-3 text-xs text-gray-500">{item.kind_label}</td>
                                    <td className="py-2 pr-3 text-xs text-gray-500">{formatDate(item.obtained_on)}</td>
                                    <td className="py-2 pr-3 text-xs">
                                        <span className="text-gray-700">{formatDate(item.due_date)}</span>
                                        {/* Le compte a rebours n'a de sens que sur une
                                            echeance encore a tenir. */}
                                        {item.tracks_due && item.days_remaining !== null && (
                                            <span className={`block ${item.days_remaining < 0 ? 'text-danger-600' : 'text-gray-400'}`}>
                                                {item.days_remaining < 0
                                                    ? `${Math.abs(item.days_remaining)} j de retard`
                                                    : `dans ${item.days_remaining} j`}
                                            </span>
                                        )}
                                    </td>
                                    <td className="py-2 pr-3">
                                        <span className={`badge text-xs ${QualificationStatusColors[item.status]}`}>
                                            {QualificationStatusLabels[item.status] ?? item.status_label}
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    )
}
