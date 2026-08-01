import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from '@/lib/store'
import { AppLayout } from '@/components/layout/AppLayout'
import { Landing } from '@/pages/Landing'
import { Login } from '@/pages/Login'
import { Register } from '@/pages/Register'
import { Dashboard } from '@/pages/Dashboard'
import { Upload } from '@/pages/Upload'
import { AnalysisResult } from '@/pages/AnalysisResult'
import { RiskDashboard } from '@/pages/RiskDashboard'
import { ClauseExplorer } from '@/pages/ClauseExplorer'
import { ContractChat } from '@/pages/ContractChat'
import { Comparison } from '@/pages/Comparison'
import { NegotiationAssistant } from '@/pages/NegotiationAssistant'
import { BeginnerMode } from '@/pages/BeginnerMode'
import { Explainability } from '@/pages/Explainability'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token } = useAuth()
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public */}
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* Protected (with sidebar layout) */}
        <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/contracts" element={<Dashboard />} />
          <Route path="/analysis/:id" element={<AnalysisResult />} />
          <Route path="/risks/:id" element={<RiskDashboard />} />
          <Route path="/risks" element={<Dashboard />} />
          <Route path="/clauses/:id" element={<ClauseExplorer />} />
          <Route path="/chat/:id" element={<ContractChat />} />
          <Route path="/compare" element={<Comparison />} />
          <Route path="/negotiate/:id" element={<NegotiationAssistant />} />
          <Route path="/negotiate" element={<Dashboard />} />
          <Route path="/beginner/:id" element={<BeginnerMode />} />
          <Route path="/explain/:id" element={<Explainability />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
