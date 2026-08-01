import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { FileText, AlertTriangle, MessageSquare, Scale, ChevronRight, GraduationCap, Brain } from 'lucide-react'
import { api } from '@/lib/api'
import { RiskGauge } from '@/components/ui/RiskGauge'
import { RiskBadge } from '@/components/ui/RiskBadge'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { categoryLabel, formatDate } from '@/lib/utils'
import type { Analysis, Clause, RiskScore, NegotiationSuggestion } from '@/types'

export function AnalysisResult() {
  const { id } = useParams<{ id: string }>()
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [clauses, setClauses] = useState<Clause[]>([])
  const [risks, setRisks] = useState<RiskScore[]>([])
  const [negotiations, setNegotiations] = useState<NegotiationSuggestion[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    api.getResults(id).then(r => {
      setAnalysis(r.analysis)
      setClauses(r.clauses)
      setRisks(r.risks)
      setNegotiations(r.negotiations)
      setLoading(false)
    })
  }, [id])

  if (loading) return <LoadingSpinner className="mt-20" />
  if (!analysis) return <p>Analysis not found</p>

  const contractRisk = (analysis.risk_score ?? 0) * 10 // scale 1-10 to 0-100

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analysis Results</h1>
          <p className="text-gray-500 mt-1">
            {analysis.contract_type?.type ?? 'Contract'} &middot; Analyzed {formatDate(analysis.created_at)}
          </p>
        </div>
        <div className="flex gap-2">
          <Link to={`/explain/${id}`} className="btn-secondary flex items-center gap-2 bg-indigo-50 text-indigo-700 border-indigo-200 hover:bg-indigo-100">
            <Brain className="w-4 h-4" /> Explain AI
          </Link>
          <Link to={`/beginner/${id}`} className="btn-secondary flex items-center gap-2 bg-purple-50 text-purple-700 border-purple-200 hover:bg-purple-100">
            <GraduationCap className="w-4 h-4" /> Beginner Mode
          </Link>
          <Link to={`/chat/${id}`} className="btn-secondary flex items-center gap-2">
            <MessageSquare className="w-4 h-4" /> Ask Questions
          </Link>
          <Link to={`/negotiate/${id}`} className="btn-primary flex items-center gap-2">
            <Scale className="w-4 h-4" /> Negotiation Help
          </Link>
        </div>
      </div>

      {/* Overview cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Risk Score */}
        <div className="card p-6 flex flex-col items-center">
          <RiskGauge score={contractRisk} size="lg" />
          <p className="mt-3 text-sm font-medium text-gray-600">Overall Contract Risk</p>
        </div>

        {/* Summary */}
        <div className="card p-6 md:col-span-2">
          <h3 className="font-semibold text-gray-900 mb-3">Executive Summary</h3>
          <p className="text-gray-700 leading-relaxed">{analysis.executive_summary}</p>
          {analysis.parties && (
            <div className="mt-4 flex gap-4">
              {analysis.parties.map((p, i) => (
                <span key={i} className="badge bg-gray-100 text-gray-700">{p.name} ({p.role})</span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Top Risks */}
      <div className="card">
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="font-semibold text-gray-900 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-red-500" /> Top Risks
          </h2>
          <Link to={`/risks/${id}`} className="text-sm text-brand-600 font-medium flex items-center gap-1">
            View All <ChevronRight className="w-4 h-4" />
          </Link>
        </div>
        <div className="divide-y divide-gray-100">
          {risks.filter(r => r.scope === 'clause').slice(0, 5).map(risk => (
            <div key={risk.id} className="px-6 py-4">
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-gray-900">{risk.explanation.slice(0, 80)}</span>
                <RiskBadge score={risk.score * 10} />
              </div>
              <p className="text-sm text-gray-600">{risk.consequence}</p>
              <span className="badge bg-gray-100 text-gray-600 mt-2">{categoryLabel(risk.category)}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Action Items */}
      {analysis.action_items && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <ActionCard title="Must Negotiate" items={analysis.action_items.negotiate} color="red" />
          <ActionCard title="Should Verify" items={analysis.action_items.verify} color="yellow" />
          <ActionCard title="Acceptable" items={analysis.action_items.acceptable} color="green" />
        </div>
      )}

      {/* Clauses Preview */}
      <div className="card">
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="font-semibold text-gray-900 flex items-center gap-2">
            <FileText className="w-5 h-5 text-gray-400" /> Clauses ({clauses.length})
          </h2>
          <Link to={`/clauses/${id}`} className="text-sm text-brand-600 font-medium flex items-center gap-1">
            Explore All <ChevronRight className="w-4 h-4" />
          </Link>
        </div>
        <div className="divide-y divide-gray-100">
          {clauses.slice(0, 5).map(clause => (
            <div key={clause.id} className="px-6 py-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-xs text-gray-400 w-6">{clause.section_number ?? clause.clause_index}</span>
                <span className="text-sm font-medium text-gray-800">{clause.title ?? categoryLabel(clause.category)}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="badge bg-brand-50 text-brand-700">{categoryLabel(clause.category)}</span>
                {clause.risk_score && <RiskBadge score={clause.risk_score * 10} />}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function ActionCard({ title, items, color }: { title: string; items?: string[]; color: string }) {
  const colors = {
    red: 'border-red-200 bg-red-50',
    yellow: 'border-yellow-200 bg-yellow-50',
    green: 'border-green-200 bg-green-50',
  }
  return (
    <div className={`card p-5 border ${colors[color as keyof typeof colors]}`}>
      <h3 className="font-semibold text-gray-900 mb-3">{title}</h3>
      {items?.length ? (
        <ul className="space-y-2">
          {items.map((item, i) => (
            <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
              <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-gray-400 flex-shrink-0" />
              {item}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-gray-500">None identified</p>
      )}
    </div>
  )
}
