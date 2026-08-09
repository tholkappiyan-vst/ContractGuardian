import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { AlertTriangle, Target, BarChart3, ChevronDown, ChevronRight, Lightbulb, Shield, Brain } from 'lucide-react'
import { api } from '@/lib/api'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { RiskBadge } from '@/components/ui/RiskBadge'

interface ClauseExplanation {
  clause_id: string
  risk_score: number
  why_risky: string
  important_words: string[]
  top_risk_factor: string | null
}

interface GlobalExplanation {
  overall_score: number
  risk_level: string
  main_concerns: Array<{
    concern: string
    severity: string
    affected_clauses: string[]
    impact: string
  }>
  dimension_breakdown: Array<{
    dimension: string
    score: number
    weight: number
    contribution: number
    clause_count: number
  }>
  recommendation: string
  action_items: string[]
  reasoning_chain: string[]
  top_risk_drivers: Array<{
    clause_id: string
    clause_title: string
    contribution_pct: number
    reason: string
  }>
  global_feature_importance: Array<{
    factor: string
    mean_contribution: number
    frequency: number
    total_impact: number
  }>
  clause_explanations: ClauseExplanation[]
  metadata: Record<string, any>
}

export function Explainability() {
  const { id } = useParams<{ id: string }>()
  const [globalData, setGlobalData] = useState<GlobalExplanation | null>(null)
  const [loadingGlobal, setLoadingGlobal] = useState(true)
  const [expandedConcern, setExpandedConcern] = useState<number | null>(null)

  useEffect(() => {
    if (!id) return
    api.explainContract(id).then(data => {
      setGlobalData(data)
      setLoadingGlobal(false)
    })
  }, [id])

  if (loadingGlobal) return <LoadingSpinner className="mt-20" />
  if (!globalData) return <p>No explanation available</p>

  const severityColor = (s: string) => {
    switch (s) {
      case 'critical': return 'bg-red-100 text-red-800'
      case 'high': return 'bg-orange-100 text-orange-800'
      case 'medium': return 'bg-yellow-100 text-yellow-800'
      default: return 'bg-green-100 text-green-800'
    }
  }

  const dimensionLabel = (d: string) => d.charAt(0).toUpperCase() + d.slice(1)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Brain className="w-6 h-6 text-purple-600" /> Explainable AI Report
          </h1>
          <p className="text-gray-500 mt-1">Understand why your contract received this risk score</p>
        </div>
      </div>

      <div className="space-y-6">
          {/* Recommendation Banner */}
          <div className={`rounded-xl p-6 border-2 ${
            globalData.risk_level === 'high' ? 'bg-red-50 border-red-200' :
            globalData.risk_level === 'medium' ? 'bg-yellow-50 border-yellow-200' :
            'bg-green-50 border-green-200'
          }`}>
            <div className="flex items-start gap-4">
              <Shield className={`w-8 h-8 flex-shrink-0 ${
                globalData.risk_level === 'high' ? 'text-red-600' :
                globalData.risk_level === 'medium' ? 'text-yellow-600' :
                'text-green-600'
              }`} />
              <div>
                <h2 className="font-bold text-lg text-gray-900">{globalData.recommendation}</h2>
                <p className="text-gray-700 mt-1">
                  Overall Score: <span className="font-bold">{globalData.overall_score}/100</span>
                  {' '}({globalData.risk_level.toUpperCase()})
                </p>
              </div>
            </div>
          </div>

          {/* Reasoning Chain */}
          {globalData.reasoning_chain.length > 0 && (
            <div className="card p-6">
              <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <Lightbulb className="w-5 h-5 text-amber-500" /> AI Reasoning Chain
              </h3>
              <div className="space-y-3">
                {globalData.reasoning_chain.map((step, i) => (
                  <div key={i} className="flex gap-3">
                    <div className="flex-shrink-0 w-7 h-7 rounded-full bg-purple-100 text-purple-700 flex items-center justify-center text-xs font-bold">
                      {i + 1}
                    </div>
                    <p className="text-gray-700 pt-1">{step}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Dimension Breakdown */}
          <div className="card p-6">
            <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-blue-500" /> Risk Dimension Breakdown
            </h3>
            <div className="space-y-3">
              {globalData.dimension_breakdown.map(d => (
                <div key={d.dimension} className="flex items-center gap-3">
                  <span className="w-28 text-sm font-medium text-gray-700">{dimensionLabel(d.dimension)}</span>
                  <div className="flex-1 h-6 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        d.score > 70 ? 'bg-red-500' : d.score > 40 ? 'bg-yellow-500' : 'bg-green-500'
                      }`}
                      style={{ width: `${d.score}%` }}
                    />
                  </div>
                  <span className="w-14 text-sm text-gray-600 text-right">{d.score.toFixed(0)}/100</span>
                  <span className="w-12 text-xs text-gray-400">{(d.weight * 100).toFixed(0)}% wt</span>
                </div>
              ))}
            </div>
          </div>

          {/* Main Concerns */}
          <div className="card p-6">
            <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-red-500" /> Main Concerns
            </h3>
            <div className="space-y-2">
              {globalData.main_concerns.map((concern, i) => (
                <div key={i} className="border border-gray-100 rounded-lg overflow-hidden">
                  <button
                    onClick={() => setExpandedConcern(expandedConcern === i ? null : i)}
                    className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition"
                  >
                    <div className="flex items-center gap-3">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${severityColor(concern.severity)}`}>
                        {concern.severity.toUpperCase()}
                      </span>
                      <span className="text-sm font-medium text-gray-900">{concern.concern}</span>
                    </div>
                    {expandedConcern === i ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                  </button>
                  {expandedConcern === i && (
                    <div className="px-4 pb-4 border-t border-gray-100 pt-3">
                      <p className="text-sm text-gray-700"><strong>Impact:</strong> {concern.impact}</p>
                      {concern.affected_clauses?.length > 0 && (
                        <p className="text-xs text-gray-500 mt-2">
                          Affected clauses: {concern.affected_clauses.join(', ')}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Global Feature Importance (SHAP) */}
          <div className="card p-6">
            <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Target className="w-5 h-5 text-indigo-500" /> Global Risk Factors (SHAP Analysis)
            </h3>
            <div className="space-y-2">
              {globalData.global_feature_importance.map((f, i) => (
                <div key={i} className="flex items-center gap-3">
                  <span className="w-56 text-sm text-gray-700 truncate">{f.factor}</span>
                  <div className="flex-1 h-4 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-indigo-500 rounded-full"
                      style={{ width: `${Math.min(100, (f.total_impact / (globalData.global_feature_importance[0]?.total_impact || 1)) * 100)}%` }}
                    />
                  </div>
                  <span className="w-10 text-xs text-gray-500">{f.frequency}x</span>
                </div>
              ))}
            </div>
          </div>

          {/* Top Risk Drivers */}
          {globalData.top_risk_drivers.length > 0 && (
            <div className="card p-6">
              <h3 className="font-semibold text-gray-900 mb-4">Top Risk Drivers</h3>
              <div className="space-y-3">
                {globalData.top_risk_drivers.map((driver, i) => (
                  <div key={i} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                    <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center text-red-700 font-bold text-sm flex-shrink-0">
                      {driver.contribution_pct}%
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">{driver.clause_title}</p>
                      <p className="text-xs text-gray-600 mt-0.5">{driver.reason}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Action Items */}
          {globalData.action_items.length > 0 && (
            <div className="card p-6">
              <h3 className="font-semibold text-gray-900 mb-4">Action Items</h3>
              <ul className="space-y-2">
                {globalData.action_items.map((item, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="mt-1.5 w-2 h-2 rounded-full bg-purple-500 flex-shrink-0" />
                    <span className="text-sm text-gray-700">{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Clause Summary Cards */}
          {globalData.clause_explanations.length > 0 && (
            <div className="card p-6">
              <h3 className="font-semibold text-gray-900 mb-4">Clause Explanations (Top {globalData.clause_explanations.length})</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {globalData.clause_explanations.map(ce => (
                  <div
                    key={ce.clause_id}
                    className="text-left p-4 border border-gray-100 rounded-lg"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <RiskBadge score={ce.risk_score * 10} />
                      {ce.top_risk_factor && (
                        <span className="text-xs text-gray-500">{ce.top_risk_factor}</span>
                      )}
                    </div>
                    <p className="text-sm text-gray-700 line-clamp-2">{ce.why_risky}</p>
                    {ce.important_words.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {ce.important_words.slice(0, 4).map(w => (
                          <span key={w} className="px-1.5 py-0.5 bg-amber-100 text-amber-800 rounded text-xs">{w}</span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
