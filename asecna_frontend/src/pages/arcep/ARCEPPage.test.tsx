/**
 * Carnet ARCEP — ce que la page doit montrer du titulaire.
 *
 * Le carnet est un document opposable : a la relecture, il doit nommer
 * l'agent, dire sa profession et son unite, et faire apparaitre les echeances
 * de ses qualifications. Ces tests verrouillent cette lecture, y compris le
 * cas ou l'alerte doit sauter aux yeux sans deplier le carnet.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'

import ARCEPPage from './ARCEPPage'
import type { ARCEPBook, User } from '../../types'

// ─── Doublures ────────────────────────────────────────────────────────────────

const BOOK: ARCEPBook = {
    id: 1,
    agent: 42,
    opened_at: '2025-03-01',
    is_active: true,
    total_hours: 18,
    entries_count: 6,
    signatures_count: 1,
    last_signed_on: '2026-10-31',
    pending_signature_count: 2,
    agent_detail: {
        id: 42, matricule: 'ASE-2024-0104', email: 'awa@asecna.org',
        first_name: 'Awa', last_name: 'Diop', full_name: 'Awa Diop',
    },
    agent_identity: {
        id: 42,
        matricule: 'ASE-2024-0104',
        last_name: 'Diop',
        first_name: 'Awa',
        full_name: 'Awa Diop',
        email: 'awa@asecna.org',
        phone: '+221 77 000 00 00',
        photo: null,
        profession: 'Contrôle de la circulation aérienne',
        profession_code: 'ATC',
        roles: ['EVALUATOR'],
        career_status: 'QUALIFIED',
        career_status_label: 'Qualifié',
        unit: {
            id: 3, code: 'DKR', name: 'ACC Dakar', unit_type: 'ACC',
            unit_type_label: 'Centre de contrôle régional (ACC)',
            location: 'Dakar', country: 'Sénégal',
        },
        hire_date: '2019-04-02',
        qualification_date: '2021-09-15',
        seniority_years: 7,
    },
    qualifications: [
        {
            kind: 'MAINTENANCE', kind_label: 'Maintien de qualification',
            label: 'Qualification CNS/ATM', issuer: '',
            obtained_on: null, due_date: '2026-10-01', tracks_due: true,
            status: 'OVERDUE', status_label: 'Controle en retard',
            days_remaining: -50, score: null, note: '',
        },
        {
            kind: 'CERTIFICATION', kind_label: 'Certification',
            label: 'Licence ATC', issuer: 'EAMAC',
            obtained_on: '2024-01-10', due_date: '2026-12-20', tracks_due: true,
            status: 'EXPIRING', status_label: 'Echeance proche',
            days_remaining: 30, score: null, note: '',
        },
    ],
    qualifications_summary: {
        total: 2, valid: 0, expiring_soon: 1, expired: 1, waived: 0,
        next_due_date: '2026-12-20', next_due_label: 'Licence ATC',
        next_due_in_days: 30, alert_level: 'CRITICAL', warning_window_days: 90,
    },
}

let book: ARCEPBook = BOOK

vi.mock('../../api', () => ({
    arcepApi: {
        books: () => Promise.resolve({ data: { count: 1, results: [book] } }),
        entries: () => Promise.resolve({ data: { count: 0, results: [] } }),
        createEntry: () => Promise.resolve({ data: {} }),
        createSignature: () => Promise.resolve({ data: {} }),
    },
}))

const CHIEF: User = {
    id: 9, matricule: 'ASE-2024-0002', email: 'chef@asecna.org',
    first_name: 'Chef', last_name: 'Unite', full_name: 'Chef Unite',
    roles: ['UNIT_CHIEF'],
}

vi.mock('../../store/authContextValue', () => ({
    useAuth: () => ({ user: CHIEF }),
}))

function renderPage() {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    return render(
        <QueryClientProvider client={client}>
            <MemoryRouter>
                <ARCEPPage />
            </MemoryRouter>
        </QueryClientProvider>,
    )
}

/** Deplie le carnet : l'en-tete d'identite n'est rendu qu'ouvert. */
async function openBook() {
    const user = userEvent.setup()
    await screen.findByText('Awa Diop')
    await user.click(screen.getByText('Awa Diop'))
    return user
}

beforeEach(() => { book = BOOK })

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('carnet ARCEP — identité du titulaire', () => {
    it('annonce la profession et l’unité sans déplier le carnet', async () => {
        renderPage()
        await screen.findByText('Awa Diop')
        expect(screen.getByText('Contrôle de la circulation aérienne')).toBeInTheDocument()
        expect(screen.getByText('DKR')).toBeInTheDocument()
    })

    it('signale une échéance dépassée dès la ligne repliée', async () => {
        renderPage()
        await screen.findByText('Awa Diop')
        expect(screen.getByText('1 échéance dépassée')).toBeInTheDocument()
        expect(screen.getByText(/2 sans visa/)).toBeInTheDocument()
    })

    it('ouvre le carnet sur le nom, le matricule et les dates clés', async () => {
        renderPage()
        await openBook()

        expect(screen.getByText('DIOP Awa')).toBeInTheDocument()
        expect(screen.getAllByText('ASE-2024-0104').length).toBeGreaterThan(0)
        expect(screen.getByText('Qualifié')).toBeInTheDocument()
        // Recrutement, qualification et ancienneté.
        expect(screen.getByText('02/04/2019')).toBeInTheDocument()
        expect(screen.getByText('15/09/2021')).toBeInTheDocument()
        expect(screen.getByText('7 ans')).toBeInTheDocument()
    })

    it('affiche les coordonnées et le rôle fonctionnel', async () => {
        renderPage()
        await openBook()
        expect(screen.getByText('awa@asecna.org')).toBeInTheDocument()
        expect(screen.getByText('+221 77 000 00 00')).toBeInTheDocument()
        expect(screen.getByText('Évaluateur')).toBeInTheDocument()
    })
})

describe('carnet ARCEP — qualifications et échéances', () => {
    it('liste chaque qualification avec son échéance et son état', async () => {
        renderPage()
        await openBook()

        expect(screen.getByText('Qualification CNS/ATM')).toBeInTheDocument()
        expect(screen.getByText('Licence ATC')).toBeInTheDocument()
        expect(screen.getByText('20/12/2026')).toBeInTheDocument()
        expect(screen.getByText('Contrôle en retard')).toBeInTheDocument()
        expect(screen.getByText('Échéance proche')).toBeInTheDocument()
    })

    it('compte les jours de retard et les jours restants', async () => {
        renderPage()
        await openBook()
        expect(screen.getByText('50 j de retard')).toBeInTheDocument()
        expect(screen.getByText('dans 30 j')).toBeInTheDocument()
    })

    it('annonce la prochaine échéance à tenir', async () => {
        renderPage()
        await openBook()
        expect(screen.getByText(/Prochaine échéance : 20\/12\/2026/)).toBeInTheDocument()
    })

    it('le dit quand l’agent n’a aucune qualification enregistrée', async () => {
        book = { ...BOOK, qualifications: [], qualifications_summary: undefined }
        renderPage()
        await openBook()
        expect(screen.getByText(/Aucune qualification enregistrée/)).toBeInTheDocument()
    })

    it('reste lisible si l’API ne sert pas encore la fiche', async () => {
        book = { ...BOOK, agent_identity: null }
        renderPage()
        await screen.findByText('Awa Diop')
        await userEvent.setup().click(screen.getByText('Awa Diop'))
        expect(screen.getByText(/Identité du titulaire indisponible/)).toBeInTheDocument()
    })
})
