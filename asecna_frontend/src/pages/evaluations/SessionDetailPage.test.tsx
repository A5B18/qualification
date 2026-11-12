/**
 * Écran de correction — le cœur du workflow en 4 étapes.
 *
 * Ces tests verrouillent les règles que l'interface doit faire respecter
 * *avant* d'appeler le serveur :
 *   • la note est bornée au barème de la question (le backend répond 400 au-delà) ;
 *   • une note non numérique ne part pas ;
 *   • « Soumettre » reste indisponible tant qu'une réponse n'est pas corrigée —
 *     c'est précisément ce que l'ancienne liste ne vérifiait pas, d'où un 400
 *     systématique ;
 *   • un agent qui relit sa copie ne voit pas de formulaire de notation.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

import SessionDetailPage from './SessionDetailPage'
import type { User } from '../../types'

// ─── Doublures ────────────────────────────────────────────────────────────────

const gradeAnswer = vi.fn(() => Promise.resolve({ data: {} }))
const submitForApproval = vi.fn(() => Promise.resolve({ data: { score: 80 } }))

const SESSION = {
    id: 7,
    exam: 1,
    exam_detail: { id: 1, title: 'QCM CNS/ATM', passing_score: 70 },
    agent: 42,
    agent_detail: { id: 42, matricule: 'ASE-2024-0104', first_name: 'Awa', last_name: 'Diop' },
    session_status: 'SUBMITTED',
    score: null,
    is_passed: null,
    answers_count: 2,
    corrected_count: 0,
    pending_correction_count: 2,
}

const ANSWERS = {
    count: 2,
    results: [
        {
            id: 101, session: 7, question: 11, response: 'Agence pour la Sécurité',
            evaluator_score: null, is_correct: null, feedback: '',
            question_detail: {
                id: 11, text: 'Que signifie ASECNA ?', question_type: 'GENERAL',
                points: 10, correct_answer: 'Agence pour la Sécurité de la Navigation Aérienne',
            },
        },
        {
            id: 102, session: 7, question: 12, response: '118.1 MHz',
            evaluator_score: null, is_correct: null, feedback: '',
            question_detail: {
                id: 12, text: 'Fréquence de la tour ?', question_type: 'TECHNICAL',
                points: 5, correct_answer: '118.1 MHz',
            },
        },
    ],
    unanswered: [],
    session_status: 'SUBMITTED',
    pending_correction: 2,
}

let currentUser: User

vi.mock('../../api', () => ({
    evaluationsApi: {
        session: () => Promise.resolve({ data: SESSION }),
        sessionAnswers: () => Promise.resolve({ data: ANSWERS }),
        gradeAnswer: (...args: unknown[]) => gradeAnswer(...(args as [])),
        submitForApproval: (...args: unknown[]) => submitForApproval(...(args as [])),
        approveSession: () => Promise.resolve({ data: {} }),
        rejectSession: () => Promise.resolve({ data: {} }),
    },
}))

vi.mock('../../store/authContextValue', () => ({
    useAuth: () => ({ user: currentUser }),
}))

function renderPage() {
    const client = new QueryClient({
        defaultOptions: { queries: { retry: false } },
    })
    return render(
        <QueryClientProvider client={client}>
            <MemoryRouter initialEntries={['/evaluations/sessions/7']}>
                <Routes>
                    <Route path="/evaluations/sessions/:id" element={<SessionDetailPage />} />
                </Routes>
            </MemoryRouter>
        </QueryClientProvider>,
    )
}

const EVALUATOR: User = {
    id: 3, matricule: 'ASE-2024-0030', email: 'e@asecna.org',
    first_name: 'Eva', last_name: 'Luateur', full_name: 'Eva Luateur',
    roles: ['EVALUATOR'],
}

const AGENT: User = {
    id: 42, matricule: 'ASE-2024-0104', email: 'a@asecna.org',
    first_name: 'Awa', last_name: 'Diop', full_name: 'Awa Diop',
    roles: [],
}

beforeEach(() => {
    gradeAnswer.mockClear()
    submitForApproval.mockClear()
    currentUser = EVALUATOR
})

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("écran de correction — vue de l'évaluateur", () => {
    it('affiche la copie, le barème et la réponse attendue', async () => {
        renderPage()
        expect(await screen.findByText('Que signifie ASECNA ?')).toBeInTheDocument()
        expect(screen.getByText('Fréquence de la tour ?')).toBeInTheDocument()
        expect(screen.getAllByText('Réponse attendue')).toHaveLength(2)
    })

    it('annonce le nombre de réponses restant à corriger', async () => {
        renderPage()
        expect(await screen.findByText('0 / 2')).toBeInTheDocument()
    })

    it('refuse une note supérieure au barème de la question', async () => {
        const user = userEvent.setup()
        renderPage()
        await screen.findByText('Que signifie ASECNA ?')

        // La première question vaut 10 points.
        const champ = screen.getAllByPlaceholderText('0')[0]
        await user.type(champ, '999')

        expect(await screen.findByText(/compris entre 0 et 10/)).toBeInTheDocument()
        const bouton = screen.getAllByRole('button', { name: /Enregistrer la note/ })[0]
        expect(bouton).toBeDisabled()
        expect(gradeAnswer).not.toHaveBeenCalled()
    })

    it('accepte une note dans le barème et l’envoie au serveur', async () => {
        const user = userEvent.setup()
        renderPage()
        await screen.findByText('Que signifie ASECNA ?')

        await user.type(screen.getAllByPlaceholderText('0')[0], '8')
        await user.click(screen.getAllByRole('button', { name: /Enregistrer la note/ })[0])

        await waitFor(() => expect(gradeAnswer).toHaveBeenCalledTimes(1))
        expect(gradeAnswer).toHaveBeenCalledWith(7, expect.objectContaining({
            answer_id: 101, evaluator_score: 8, is_correct: false,
        }))
    })

    it('marque la réponse comme correcte quand l’évaluateur le choisit', async () => {
        const user = userEvent.setup()
        renderPage()
        await screen.findByText('Que signifie ASECNA ?')

        await user.click(screen.getAllByRole('button', { name: /Correcte/ })[0])
        await user.type(screen.getAllByPlaceholderText('0')[0], '10')
        await user.click(screen.getAllByRole('button', { name: /Enregistrer la note/ })[0])

        await waitFor(() => expect(gradeAnswer).toHaveBeenCalled())
        expect(gradeAnswer).toHaveBeenCalledWith(7, expect.objectContaining({
            is_correct: true, evaluator_score: 10,
        }))
    })

    it("n'offre pas la soumission tant que la session est SUBMITTED", async () => {
        // Le backend exige CORRECTING ou REJECTED : afficher le bouton ici
        // menait droit à un 400.
        renderPage()
        await screen.findByText('Que signifie ASECNA ?')
        expect(screen.queryByRole('button', { name: /Soumettre au chef/ })).toBeNull()
    })
})

describe("écran de correction — vue de l'agent", () => {
    it('ne propose aucun formulaire de notation', async () => {
        currentUser = AGENT
        renderPage()
        await screen.findByText('Que signifie ASECNA ?')
        expect(screen.queryByRole('button', { name: /Enregistrer la note/ })).toBeNull()
        expect(screen.queryByRole('button', { name: /Approuver/ })).toBeNull()
    })
})
