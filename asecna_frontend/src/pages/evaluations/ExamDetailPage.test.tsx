/**
 * Composition d'un examen — le QCM est le seul format.
 *
 * Ces tests verrouillent ce que l'ecran doit empecher avant d'appeler le
 * serveur : une question sans propositions, des propositions en doublon, ou
 * une bonne reponse qui n'est pas l'une des options. Le backend refuse les
 * trois (migration 0003 et `Question.clean()`) ; l'ecran ne doit pas y
 * envoyer l'evaluateur pour rien.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

import ExamDetailPage from './ExamDetailPage'
import type { User } from '../../types'

const createQuestion = vi.fn(() => Promise.resolve({ data: { id: 77 } }))
const updateExam = vi.fn(() => Promise.resolve({ data: {} }))

const EXAM = {
    id: 5, title: 'QCM CNS/ATM', training: 1,
    training_detail: { id: 1, title: 'Qualification CNS' },
    questions: [], duration_minutes: 60, passing_score: 70,
    exam_status: 'DRAFT',
}

vi.mock('../../api', () => ({
    evaluationsApi: {
        exam: () => Promise.resolve({ data: EXAM }),
        questions: () => Promise.resolve({ data: { count: 0, results: [] } }),
        createQuestion: (...args: unknown[]) => createQuestion(...(args as [])),
        updateExam: (...args: unknown[]) => updateExam(...(args as [])),
        publishExam: () => Promise.resolve({ data: {} }),
        unpublishExam: () => Promise.resolve({ data: {} }),
    },
    trainingApi: {
        trainings: () => Promise.resolve({ data: { count: 0, results: [] } }),
    },
}))

const EVALUATOR: User = {
    id: 3, matricule: 'ASE-2024-0030', email: 'e@asecna.org',
    first_name: 'Eva', last_name: 'Luateur', full_name: 'Eva Luateur',
    roles: ['EVALUATOR'],
}

vi.mock('../../store/authContextValue', () => ({
    useAuth: () => ({ user: EVALUATOR }),
}))

function renderPage() {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    return render(
        <QueryClientProvider client={client}>
            <MemoryRouter initialEntries={['/evaluations/exams/5']}>
                <Routes>
                    <Route path="/evaluations/exams/:id" element={<ExamDetailPage />} />
                </Routes>
            </MemoryRouter>
        </QueryClientProvider>,
    )
}

/** Ouvre le formulaire de creation de question. */
async function openForm() {
    const user = userEvent.setup()
    await user.click(await screen.findByRole('button', { name: /Nouvelle question/ }))
    return user
}

beforeEach(() => {
    createQuestion.mockClear()
    updateExam.mockClear()
})

describe('composition — formulaire QCM', () => {
    it("n'offre plus le choix du format", async () => {
        renderPage()
        await openForm()
        // Le format est annoncé, pas choisi : aucune liste déroulante,
        // et surtout plus de « Vrai / Faux » ni de « Réponse ouverte ».
        expect(screen.getByText('QCM')).toBeInTheDocument()
        expect(screen.queryByText('Vrai / Faux')).toBeNull()
        expect(screen.queryByText('Réponse ouverte')).toBeNull()
    })

    it('fait désigner la bonne réponse parmi les options', async () => {
        renderPage()
        await openForm()
        expect(screen.getByText(/cochez la bonne réponse/i)).toBeInTheDocument()
        // Quatre options proposées par défaut, donc quatre boutons radio.
        expect(screen.getAllByRole('radio')).toHaveLength(4)
        // Et plus de champ libre « Réponse attendue ».
        expect(screen.queryByText('Réponse attendue')).toBeNull()
    })

    it('refuse un QCM sans au moins deux propositions', async () => {
        renderPage()
        const user = await openForm()

        await user.type(screen.getByRole('textbox', { name: 'Énoncé' }), 'Quelle est la bande VOR ?')
        await user.type(screen.getByPlaceholderText('Option 1'), '108 MHz')

        expect(await screen.findByText(/au moins 2 options/)).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /Créer et rattacher/ })).toBeDisabled()
        expect(createQuestion).not.toHaveBeenCalled()
    })

    it('refuse deux propositions identiques', async () => {
        renderPage()
        const user = await openForm()

        await user.type(screen.getByRole('textbox', { name: 'Énoncé' }), 'Énoncé')
        await user.type(screen.getByPlaceholderText('Option 1'), 'Vrai')
        await user.type(screen.getByPlaceholderText('Option 2'), 'vrai')

        expect(await screen.findByText(/options sont identiques/)).toBeInTheDocument()
        expect(createQuestion).not.toHaveBeenCalled()
    })

    it('refuse une bonne réponse cochée sur une option vide', async () => {
        renderPage()
        const user = await openForm()

        await user.type(screen.getByRole('textbox', { name: 'Énoncé' }), 'Énoncé')
        await user.type(screen.getByPlaceholderText('Option 1'), 'Vrai')
        await user.type(screen.getByPlaceholderText('Option 2'), 'Faux')
        // La coche part sur la troisième ligne, restée vide.
        await user.click(screen.getAllByRole('radio')[2])

        expect(await screen.findByText(/Cochez laquelle des options/)).toBeInTheDocument()
        expect(createQuestion).not.toHaveBeenCalled()
    })

    it("envoie l'option cochée comme bonne réponse, sans les options vides", async () => {
        renderPage()
        const user = await openForm()

        await user.type(screen.getByRole('textbox', { name: 'Énoncé' }), 'Quelle est la bande VOR ?')
        await user.type(screen.getByPlaceholderText('Option 1'), '108 - 117,975 MHz')
        await user.type(screen.getByPlaceholderText('Option 2'), '329 - 335 MHz')
        await user.click(screen.getAllByRole('radio')[1])
        await user.click(screen.getByRole('button', { name: /Créer et rattacher/ }))

        await waitFor(() => expect(createQuestion).toHaveBeenCalledTimes(1))
        expect(createQuestion).toHaveBeenCalledWith(expect.objectContaining({
            question_kind: 'MCQ',
            correct_answer: '329 - 335 MHz',
            options: ['108 - 117,975 MHz', '329 - 335 MHz'],
        }))
    })

    it('permet d’ajouter une option jusqu’au plafond de six', async () => {
        renderPage()
        const user = await openForm()

        await user.click(screen.getByRole('button', { name: /Ajouter une option/ }))
        expect(screen.getAllByRole('radio')).toHaveLength(5)
        await user.click(screen.getByRole('button', { name: /Ajouter une option/ }))
        expect(screen.getAllByRole('radio')).toHaveLength(6)
        // Plafond atteint : le bouton disparaît.
        expect(screen.queryByRole('button', { name: /Ajouter une option/ })).toBeNull()
    })
})
