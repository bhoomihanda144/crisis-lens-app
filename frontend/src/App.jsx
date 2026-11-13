import { Routes, Route, Link } from 'react-router-dom'
import AppShell from './components/layout/AppShell'
import EmptyState from './components/ui/EmptyState'
import Button from './components/ui/Button'
import OverviewPage from './pages/OverviewPage'
import IncidentMapPage from './pages/IncidentMapPage'
import IncidentQueuePage from './pages/IncidentQueuePage'
import AiAnalysisPage from './pages/AiAnalysisPage'
import EvidenceGraphPage from './pages/EvidenceGraphPage'
import RescuePriorityPage from './pages/RescuePriorityPage'
import SimulationPage from './pages/SimulationPage'
import VerificationPage from './pages/VerificationPage'
import IncidentDetailsPage from './pages/IncidentDetailsPage'
import ApiTestPage from './pages/ApiTestPage'

function NotFound() {
  return (
    <EmptyState
      title="Page not found"
      description="That address does not exist in CrisisLens."
      action={
        <Link to="/">
          <Button>Back to overview</Button>
        </Link>
      }
    />
  )
}

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<OverviewPage />} />
        <Route path="map" element={<IncidentMapPage />} />
        <Route path="incidents" element={<IncidentQueuePage />} />
        <Route path="incidents/:id" element={<IncidentDetailsPage />} />
        <Route path="analysis" element={<AiAnalysisPage />} />
        <Route path="graph" element={<EvidenceGraphPage />} />
        <Route path="graph/:id" element={<EvidenceGraphPage />} />
        <Route path="priority" element={<RescuePriorityPage />} />
        <Route path="simulation" element={<SimulationPage />} />
        <Route path="verification" element={<VerificationPage />} />
        <Route path="api-test" element={<ApiTestPage />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}