import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { AlertTriangle, ShieldAlert, TrendingDown } from 'lucide-react'
import { api } from '@/lib/api'
import { RiskGauge } from '@/components/ui/RiskGauge'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { categoryLabel, cn } from '@/lib/utils'
import type { RiskScore } from '@/types'

export function RiskDashboard() {
  const { id } = useParams<{ id: string }>()
  const [risks, setRisks] = useState<RiskScore[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>('all')

  useEffect(() => {
    if (!id) return
    api.getRisks(id).then(r => { setRisks(r); setLoading(false) })
  }, [id])

  if (loading) return <LoadingSpinner className="mt-20" />

  const clauseRisks = risks.filter(r => r.scope === 'clause')
  const contractRisk = risks.find(r => r.scope === 'contract')
  const compounding = risks.filter(r => r.scope === 'compounding')

  const categories = [...new Set(clauseRisks.map(r => r.category))]
  const filtered = filter === 'all' ? clauseRisks : clauseRisks.filter(r => r.category === filter)

  // Distribution
  const critical = clauseRisks.filter(r => r.score >= 9).length
  const high = clauseRisks.filter(r => r.score >= 7 && r.score < 9).length
  const moderate = clauseRisks.filter(r => r.score >= 4 && r.score < 7).length
  const low = clauseRisks.filter(r => r.score < 4).length

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-gray-900">Risk Dashboard</h1>

      {/* Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card p-6 flex flex-col items-center">
          <RiskGauge score={(contractRisk?.score ?? 5) * 10} size="md" />
          <p className="text-sm text-gray-500 mt-2">Overall Score</p>
        </div>
        <RiskStat icon={ShieldAlert} label="Critical" count={critical} color="text-red-600 bg-red-50" />
        <RiskStat icon={AlertTriangle} label="High" count={high} color="text-orange-600 bg-orange-50" />
        <RiskStat icon={TrendingDown} label="Low Risk" count={low} color="text-green-600 bg-green-50" />
      </div>

      {/* Risk Distribution Bar */}
      <div className="card p-6">
        <h3 className="font-semibold text-gray-900 mb-4">Risk Distribution</h3>
        <div className="flex h-6 rounded-full overflow-hidden">
          {critical > 0 && <div className="bg-red-500" style={{ width: `${(critical / clauseRisks.length) * 100}%` }} />}
          {high > 0 && <div className="bg-orange-400" style={{ width: `${(high / clauseRisks.length) * 100}%` }} />}
          {moderate > 0 && <div className="bg-yellow-400" style={{ width: `${(moderate / clauseRisks.length) * 100}%` }} />}
          {low > 0 && <div className="bg-green-400" style={{ width: `${(low / clauseRisks.length) * 100}%` }} />}
        </div>
        <div className="flex items-center gap-4 mt-3 text-xs text-gray-600">
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-red-500" /> Critical ({critical})</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-orange-400" /> High ({high})</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-yellow-400" /> Moderate ({moderate})</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-green-400" /> Low ({low})</span>
        </div>
      </div>

      {/* Compounding Risks */}
      {compounding.length > 0 && (
        <div className="card p-6 border-red-200 bg-red-50">
          <h3 className="font-semibold text-red-900 mb-3 flex items-center gap-2">
            <ShieldAlert className="w-5 h-5" /> Compounding Risks
          </h3>
          <div className="space-y-3">
            {compounding.map(r => (
              <div key={r.id} className="p-3 bg-white rounded-lg border border-red-100">
                <p className="text-sm text-gray-800">{r.explanation}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Category Filter */}
      <div className="flex items-center gap-2 flex-wrap">
        <button onClick={() => setFilter('all')}
          className={cn('badge cursor-pointer', filter === 'all' ? 'bg-brand-100 text-brand-800' : 'bg-gray-100 text-gray-600')}>
          All ({clauseRisks.length})
        </button>
        {categories.map(cat => (
          <button key={cat} onClick={() => setFilter(cat)}
            className={cn('badge cursor-pointer', filter === cat ? 'bg-brand-100 text-brand-800' : 'bg-gray-100 text-gray-600')}>
            {categoryLabel(cat)}
          </button>
        ))}
      </div>

      {/* Risk List */}
      <div className="space-y-3">
        {filtered.map(risk => (
          <div key={risk.id} className="card p-5">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <ScoreIndicator score={risk.score} />
                  <span className="font-medium text-gray-900">{risk.explanation}</span>
                </div>
                <p className="text-sm text-gray-600 ml-9">{risk.consequence}</p>
                {risk.standard_note && (
                  <p className="text-xs text-gray-500 ml-9 mt-2 italic">
                    Standard: {risk.standard_note}
                  </p>
                )}
              </div>
              <span className="badge bg-gray-100 text-gray-600">{categoryLabel(risk.category)}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function RiskStat({ icon: Icon, label, count, color }: {
  icon: React.ElementType; label: string; count: number; color: string
}) {
  return (
    <div className="card p-5 flex items-center gap-4">
      <div className={cn('w-10 h-10 rounded-lg flex items-center justify-center', color.split(' ')[1])}>
        <Icon className={cn('w-5 h-5', color.split(' ')[0])} />
      </div>
      <div>
        <p className="text-2xl font-bold text-gray-900">{count}</p>
        <p className="text-sm text-gray-500">{label}</p>
      </div>
    </div>
  )
}

function ScoreIndicator({ score }: { score: number }) {
  const color = score >= 9 ? 'bg-red-500' : score >= 7 ? 'bg-orange-400' : score >= 4 ? 'bg-yellow-400' : 'bg-green-400'
  return (
    <div className="flex items-center gap-1.5">
      <div className={cn('w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-bold', color)}>
        {score}
      </div>
    </div>
  )
}
