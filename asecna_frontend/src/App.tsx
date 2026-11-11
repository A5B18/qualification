import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './store/AuthContext'
import { useAuth } from './store/authContextValue'
import Layout from './components/Layout'
import LoginPage from './pages/auth/LoginPage'
import DashboardPage from './pages/dashboard/DashboardPage'
import AgentsPage from './pages/agents/AgentsPage'
import AgentDetailPage from './pages/agents/AgentDetailPage'
import ProbationPage from './pages/probation/ProbationPage'
import MentoringPage from './pages/mentoring/MentoringPage'
import ARCEPPage from './pages/arcep/ARCEPPage'
import EvaluationsPage from './pages/evaluations/EvaluationsPage'
import ReportsPage from './pages/reports/ReportsPage'
import TrainingPage from './pages/training/TrainingPage'
import QualificationMaintenancePage from './pages/training/QualificationMaintenancePage'
import UnitsPage from './pages/units/UnitsPage'
import NotFoundPage from './pages/NotFoundPage'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()
  if (isLoading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-asecna-600" />
    </div>
  )
  return user ? <>{children}</> : <Navigate to="/login" replace />
}

function AppRoutes() {
  const { user } = useAuth()
  return (
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
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/training" element={<TrainingPage />} />
        <Route path="/training/maintenances" element={<QualificationMaintenancePage />} />
        <Route path="/units" element={<UnitsPage />} />
      </Route>
      {/* Sans cette route, une URL inconnue affichait une page blanche */}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}
