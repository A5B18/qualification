/**
 * Carnets ARCEP — releve d'activites vise par le chef d'unite.
 *
 * Le carnet ne montrait que le nom du titulaire et ses entrees. C'est un
 * document opposable : a l'ouverture, il doit porter l'identite complete de
 * l'agent (nom, prenom, matricule, profession, unite), l'etat de ses
 * qualifications avec leurs echeances, et l'etat des visas. Ces trois blocs
 * sont servis par le backend dans `agent_identity`, `qualifications` et
 * `qualifications_summary`.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { arcepApi } from '../../api'
import { useAuth } from '../../store/authContextValue'
import {
    BookMarked, Calendar, Clock, Plus, X,
    PenLine, ChevronDown, ChevronUp, CheckCircle, Hourglass,
    Briefcase, Building2,
} from 'lucide-react'
import { useState } from 'react'
import { apiErrorMessage } from '../../api/client'
import {
    AgentIdentityCard, QualificationsPanel, QualificationAlertBadge, SectionTitle,
} from '../../components/ARCEPBookSections'
import type { User, ARCEPBook, ARCEPEntry } from '../../types'
import { formatDate } from '../../utils/dates'
import { hasRole } from '../../utils/roles'

/** Seul le chef d'unité vise un carnet (backend : `IsUnitChief`). */
const canSign = (user: User | null) => hasRole(user, 'UNIT_CHIEF')
export default function ARCEPPage() {
    const { user } = useAuth()
    const qc = useQueryClient()
    const [flash, setFlash] = useState<{ text: string; ok: boolean } | null>(null)
    const [expandedBook, setExpandedBook] = useState<number | null>(null)
    const [addEntryBookId, setAddEntryBookId] = useState<number | null>(null)
    const [signBookId, setSignBookId] = useState<number | null>(null)
    const [entryForm, setEntryForm] = useState({ activity: '', duration_hours: 1, notes: '' })
    const [signNotes, setSignNotes] = useState('')

    const notify = (text: string, ok = true) => {
        setFlash({ text, ok })
        setTimeout(() => setFlash(null), 4000)
    }

    const { data: booksData, isLoading } = useQuery({
        queryKey: ['arcep-books'],
        queryFn: () => arcepApi.books().then(r => r.data),
    })
    const books = booksData?.results ?? []
    const totalHoursAll = books.reduce((s: number, b: ARCEPBook) => s + Number(b.total_hours ?? 0), 0)
    const pendingVisas = books.reduce(
        (s: number, b: ARCEPBook) => s + Number(b.pending_signature_count ?? 0), 0,
    )
    const overdueBooks = books.filter(
        (b: ARCEPBook) => (b.qualifications_summary?.expired ?? 0) > 0,
    ).length

    const createEntryMut = useMutation({
        mutationFn: (data: Record<string, unknown>) => arcepApi.createEntry(data),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['arcep-books'] })
            qc.invalidateQueries({ queryKey: ['arcep-entries'] })
            setAddEntryBookId(null)
            setEntryForm({ activity: '', duration_hours: 1, notes: '' })
            notify('✅ Entrée ajoutée')
        },
        onError: (e: unknown) => notify(apiErrorMessage(e, "❌ Impossible d'ajouter l'entrée"), false),
    })

    const signMut = useMutation({
        // `comment` est le champ du modèle ; la période est calculée par le
        // backend à partir des entrées encore non signées.
        mutationFn: (bookId: number) =>
            arcepApi.createSignature({ book: bookId, comment: signNotes }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['arcep-books'] })
            setSignBookId(null)
            setSignNotes('')
            notify('✅ Carnet signé')
        },
        onError: (e: unknown) => notify(apiErrorMessage(e, '❌ Erreur signature'), false),
    })

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                    <BookMarked size={24} className="text-success-600" /> Carnets ARCEP
                </h1>
                <p className="text-gray-400 text-sm mt-0.5">{booksData?.count ?? 0} carnets · {totalHoursAll}h cumulées</p>
            </div>

            {flash && (
                <div className={`p-3 rounded-xl text-sm border ${flash.ok ? 'bg-success-50 border-success-200 text-success-800' : 'bg-danger-50 border-danger-200 text-danger-800'}`}>
                    {flash.text}
                </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="card text-center py-4">
                    <div className="text-3xl font-bold text-success-600">
                        {books.filter((b: ARCEPBook) => b.is_active).length}
                    </div>
                    <div className="text-sm text-gray-500 mt-1">Carnets actifs</div>
                </div>
                <div className="card text-center py-4">
                    <div className="text-3xl font-bold text-info-600">{totalHoursAll}h</div>
                    <div className="text-sm text-gray-500 mt-1">Total heures</div>
                </div>
                {/* Les deux indicateurs qui decident d'une action : des visas en
                    retard, et des qualifications dont l'echeance est passee. */}
                <div className="card text-center py-4">
                    <div className="text-3xl font-bold text-accent-600">{pendingVisas}</div>
                    <div className="text-sm text-gray-500 mt-1">Entrées sans visa</div>
                </div>
                <div className="card text-center py-4">
                    <div className={`text-3xl font-bold ${overdueBooks > 0 ? 'text-danger-600' : 'text-gray-400'}`}>
                        {overdueBooks}
                    </div>
                    <div className="text-sm text-gray-500 mt-1">Carnets en alerte d'échéance</div>
                </div>
            </div>

            {isLoading ? (
                <div className="flex items-center justify-center h-40">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-success-600" />
                </div>
            ) : books.length === 0 ? (
                <div className="card text-center py-16 text-gray-400">
                    <BookMarked size={48} className="mx-auto mb-3 opacity-30" />
                    <p className="font-medium">Aucun carnet ARCEP</p>
                    <p className="text-sm mt-1">Les carnets sont créés automatiquement à l'arrivée d'un agent</p>
                </div>
            ) : (
                <div className="space-y-3">
                    {books.map((book: ARCEPBook) => (
                        <ARCEPBookRow
                            key={book.id}
                            book={book}
                            expanded={expandedBook === book.id}
                            onToggle={() => setExpandedBook(expandedBook === book.id ? null : book.id)}
                            onAddEntry={() => { setAddEntryBookId(book.id); setEntryForm({ activity: '', duration_hours: 1, notes: '' }) }}
                            onSign={() => { setSignBookId(book.id); setSignNotes('') }}
                            canSign={canSign(user)}
                            isOwnBook={book.agent === user?.id}
                        />
                    ))}
                </div>
            )}

            {/* Modal : Ajouter une entrée */}
            {addEntryBookId !== null && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
                    <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-md">
                        <div className="flex items-center justify-between mb-5">
                            <h3 className="text-lg font-bold text-gray-900">Ajouter une entrée</h3>
                            <button onClick={() => setAddEntryBookId(null)} className="p-1 hover:bg-gray-100 rounded-lg">
                                <X size={18} className="text-gray-400" />
                            </button>
                        </div>
                        <form onSubmit={e => {
                            e.preventDefault()
                            createEntryMut.mutate({ ...entryForm, book: addEntryBookId, entry_date: new Date().toISOString().split('T')[0] })
                        }} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Activité *</label>
                                <input required type="text" value={entryForm.activity}
                                    onChange={e => setEntryForm(f => ({ ...f, activity: e.target.value }))}
                                    placeholder="Ex: Maintenance système CNS, Test radar..."
                                    className="w-full border border-gray-200 rounded-xl p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-success-500" />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Durée (heures) *</label>
                                <input required type="number" min="0.5" max="24" step="0.5"
                                    value={entryForm.duration_hours}
                                    onChange={e => setEntryForm(f => ({ ...f, duration_hours: Number(e.target.value) }))}
                                    className="w-full border border-gray-200 rounded-xl p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-success-500" />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
                                <textarea value={entryForm.notes}
                                    onChange={e => setEntryForm(f => ({ ...f, notes: e.target.value }))}
                                    rows={3} placeholder="Observations, remarques..."
                                    className="w-full border border-gray-200 rounded-xl p-2.5 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-success-500" />
                            </div>
                            <div className="flex gap-3 justify-end pt-2">
                                <button type="button" onClick={() => setAddEntryBookId(null)} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-xl">Annuler</button>
                                <button type="submit" disabled={createEntryMut.isPending}
                                    className="px-4 py-2 text-sm font-medium text-white bg-success-600 hover:bg-success-700 rounded-xl disabled:opacity-50">
                                    {createEntryMut.isPending ? 'Ajout...' : 'Ajouter'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Modal : Signer */}
            {signBookId !== null && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
                    <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-md">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-bold text-gray-900">Signer le carnet ARCEP</h3>
                            <button onClick={() => setSignBookId(null)} className="p-1 hover:bg-gray-100 rounded-lg">
                                <X size={18} className="text-gray-400" />
                            </button>
                        </div>
                        <p className="text-sm text-gray-500 mb-4">La signature couvre toutes les entrées non encore signées.</p>
                        <textarea value={signNotes} onChange={e => setSignNotes(e.target.value)}
                            rows={3} placeholder="Observations du chef d'unité (optionnel)..."
                            className="w-full border border-gray-200 rounded-xl p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-info-500" />
                        <div className="flex gap-3 mt-4 justify-end">
                            <button onClick={() => setSignBookId(null)} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-xl">Annuler</button>
                            <button disabled={signMut.isPending}
                                onClick={() => signMut.mutate(signBookId!)}
                                className="px-4 py-2 text-sm text-white bg-info-600 hover:bg-info-700 rounded-xl flex items-center gap-2 disabled:opacity-50">
                                <CheckCircle size={14} /> Signer
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

function ARCEPBookRow({ book, expanded, onToggle, onAddEntry, onSign, canSign, isOwnBook }: {
    book: ARCEPBook; expanded: boolean
    onToggle: () => void; onAddEntry: () => void; onSign: () => void
    canSign: boolean; isOwnBook: boolean
}) {
    const { data: entriesData } = useQuery({
        queryKey: ['arcep-entries', book.id],
        queryFn: () => arcepApi.entries(book.id).then(r => r.data),
        enabled: expanded,
    })
    const entries = entriesData?.results ?? []
    const totalH = entries.reduce((s: number, e: ARCEPEntry) => s + Number(e.duration_hours), 0)
    const identity = book.agent_identity ?? null
    const summary = book.qualifications_summary

    return (
        <div className="card p-0 overflow-hidden">
            <div className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50 transition-colors" onClick={onToggle}>
                <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-xl bg-success-100 flex items-center justify-center">
                        <BookMarked size={18} className="text-success-700" />
                    </div>
                    <div>
                        <div className="font-semibold text-gray-900">
                            {identity?.full_name
                                ?? (book.agent_detail
                                    ? `${book.agent_detail.first_name} ${book.agent_detail.last_name}`
                                    : `Agent #${book.agent}`)}
                        </div>
                        <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                            <span className="text-xs text-gray-400 font-mono">
                                {identity?.matricule ?? book.agent_detail?.matricule}
                            </span>
                            {identity?.profession && (
                                <span className="text-xs text-gray-500 flex items-center gap-1">
                                    <Briefcase size={10} /> {identity.profession}
                                </span>
                            )}
                            {identity?.unit && (
                                <span className="text-xs text-gray-500 flex items-center gap-1">
                                    <Building2 size={10} /> {identity.unit.code}
                                </span>
                            )}
                        </div>
                    </div>
                </div>
                <div className="flex items-center gap-4">
                    <div className="text-right hidden sm:block">
                        <div className="text-sm font-semibold text-gray-700">{book.total_hours ?? totalH}h</div>
                        <div className="text-xs text-gray-400">cumulées</div>
                    </div>
                    <div className="flex items-center gap-2">
                        {/* Ce qui doit sauter aux yeux sans deplier le carnet :
                            l'etat des echeances et les entrees sans visa. */}
                        <QualificationAlertBadge summary={summary} />
                        {(book.pending_signature_count ?? 0) > 0 && (
                            <span className="badge text-xs bg-accent-100 text-accent-700 flex items-center gap-1"
                                title="Entrées non couvertes par une signature du chef d'unité">
                                <Hourglass size={10} /> {book.pending_signature_count} sans visa
                            </span>
                        )}
                        <span className={`badge text-xs ${book.is_active ? 'bg-success-100 text-success-700' : 'bg-gray-100 text-gray-500'}`}>
                            {book.is_active ? 'Actif' : 'Inactif'}
                        </span>
                        {(isOwnBook || canSign) && (
                            <button onClick={e => { e.stopPropagation(); onAddEntry() }}
                                className="text-xs flex items-center gap-1 px-2 py-1 bg-success-100 text-success-700 hover:bg-success-200 rounded-lg"
                                title="Ajouter une entrée">
                                <Plus size={12} /> Entrée
                            </button>
                        )}
                        {canSign && (
                            <button onClick={e => { e.stopPropagation(); onSign() }}
                                className="text-xs flex items-center gap-1 px-2 py-1 bg-info-100 text-info-700 hover:bg-info-200 rounded-lg"
                                title="Signer le carnet">
                                <PenLine size={12} /> Signer
                            </button>
                        )}
                    </div>
                    {expanded ? <ChevronUp size={16} className="text-gray-400" /> : <ChevronDown size={16} className="text-gray-400" />}
                </div>
            </div>

            {expanded && (
                <div className="border-t border-gray-100 p-4 space-y-5">
                    {/* Premiere page du carnet : le titulaire. */}
                    <AgentIdentityCard identity={identity} book={book} />

                    {/* Deuxieme page : qualifications et echeances. */}
                    <QualificationsPanel
                        items={book.qualifications ?? []}
                        summary={summary}
                    />

                    <div>
                        <SectionTitle icon={<Clock size={12} />} label="Relevé d'activités" />
                        {entries.length === 0 ? (
                            <p className="text-sm text-gray-400 text-center py-4">Aucune entrée pour ce carnet</p>
                        ) : (
                            <div className="space-y-2">
                                <div className="text-xs text-gray-400 mb-3">
                                    {entries.length} entrée(s) — {totalH}h total
                                </div>
                                {entries.map((entry: ARCEPEntry) => (
                                    <div key={entry.id} className="flex items-start justify-between p-3 bg-gray-50 rounded-xl">
                                        <div>
                                            <div className="text-sm font-medium text-gray-900">{entry.activity}</div>
                                            {entry.notes && <div className="text-xs text-gray-500 mt-0.5">{entry.notes}</div>}
                                            <div className="flex items-center gap-3 mt-1">
                                                <span className="text-xs text-gray-400 flex items-center gap-1">
                                                    <Calendar size={10} /> {formatDate(entry.entry_date)}
                                                </span>
                                                <span className="text-xs text-gray-400 flex items-center gap-1">
                                                    <Clock size={10} /> {entry.duration_hours}h
                                                </span>
                                            </div>
                                        </div>
                                        {/* Une entree non visee n'est pas officielle : le dire
                                            plutot que de n'afficher aucun signe. */}
                                        {entry.is_validated ? (
                                            <span className="text-xs text-success-600 flex items-center gap-1 flex-shrink-0 mt-0.5">
                                                <CheckCircle size={12} aria-hidden="true" /> Visée
                                            </span>
                                        ) : (
                                            <span className="text-xs text-gray-400 flex items-center gap-1 flex-shrink-0 mt-0.5">
                                                <Hourglass size={12} aria-hidden="true" /> En attente de visa
                                            </span>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    )
}
