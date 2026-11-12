import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './store/AuthContext'
import { useAuth } from './store/authContextValue'
import Layout from './components/Layout'
import LoginPage from './pages/auth/LoginPage'

/**
 * Chargement différé des pages.
 *
 * L'application partait en un seul paquet de plus de 800 kB, téléchargé en
 * entier avant le premier écran — y compris les écrans d'administration qu'un
 * agent ne verra jamais. Chaque route a désormais son propre morceau.
 *
 * `LoginPage` reste en chargement immédiat : c'est le premier écran d'un
 * visiteur non connecté, le différer ajouterait une attente visible.
 */
const DashboardPage = lazy(() => import('./pages/dashboard/DashboardPage'))
const AgentsPage = lazy(() => import('./pages/agents/AgentsPage'))
const AgentDetailPage = lazy(() => import('./pages/agents/AgentDetailPage'))
const ProbationPage = lazy(() => import('./pages/probation/ProbationPage'))
const MentoringPage = lazy(() => import('./pages/mentoring/MentoringPage'))
const ARCEPPage = lazy(() => import('./pages/arcep/ARCEPPage'))
const EvaluationsPage = lazy(() => import('./pages/evaluations/EvaluationsPage'))
const SessionDetailPage = lazy(() => import('./pages/evaluations/SessionDetailPage'))
const ExamDetailPage = lazy(() => import('./pages/evaluations/ExamDetailPage'))
const TakeExamPage = lazy(() => import('./pages/evaluations/TakeExamPage'))
const ReportsPage = lazy(() => import('./pages/reports/ReportsPage'))
const TrainingPage = lazy(() => import('./pages/training/TrainingPage'))
const QualificationMaintenancePage = lazy(() => import('./pages/training/QualificationMaintenancePage'))
const UnitsPage = lazy(() => import('./pages/units/UnitsPage'))
const WorkflowsPage = lazy(() => import('./pages/workflows/WorkflowsPage'))
const AuditPage = lazy(() => import('./pages/audit/AuditPage'))
const UsersPage = lazy(() => import('./pages/users/UsersPage'))
const ProfilePage = lazy(() => import('./pages/profile/ProfilePage'))
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'))

function Spinner() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-asecna-600" />
    </div>
  )
}

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()
  if (isLoading) return <Spinner />
  return user ? <>{children}</> : <Navigate to="/login" replace />
}

function AppRoutes() {
  const { user } = useAuth()
  return (
    <Suspense fallback={<Spinner />}>
      <Routes>
        <Route path="/login" element={user ? <Navigate to="/dashboard" /> : <LoginPage />} />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route element={<PrivateRoute><Layout /></PrivateRoute>}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/agents" element={<AgentsPage />} />
          <Route path="/agents/:id" element={<AgentDetailPage />} />
          <Route path="/probation" element={<ProbationPage />} />
          <Route path="/mentoring" element={<MentoringPage />} />
          <Route path="/arcep" element={<ARCEPPage />} />
          <Route path="/evaluations" element={<EvaluationsPage />} />
          {/* Correction réponse par réponse : c'est cet écran qui porte le
              workflow en 4 étapes (corriger, soumettre, approuver, rejeter). */}
          <Route path="/evaluations/sessions/:id" element={<SessionDetailPage />} />
          {/* Composition d'un examen (évaluateur) et passage de l'épreuve (agent) */}
          <Route path="/evaluations/exams/:id" element={<ExamDetailPage />} />
          <Route path="/evaluations/exams/:id/compose" element={<TakeExamPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/training" element={<TrainingPage />} />
          <Route path="/training/maintenances" element={<QualificationMaintenancePage />} />
          <Route path="/units" element={<UnitsPage />} />
          {/* Registre transversal : tout ce qui attend une decision,
              tous modules confondus. */}
          <Route path="/workflows" element={<WorkflowsPage />} />
          {/* Écrans d'administration : le backend renvoie 403 aux autres rôles,
              les pages l'annoncent au lieu d'afficher une erreur brute. */}
          <Route path="/users" element={<UsersPage />} />
          <Route path="/audit" element={<AuditPage />} />
          <Route path="/profile" element={<ProfilePage />} />
        </Route>
        {/* Sans cette route, une URL inconnue affichait une page blanche */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}
