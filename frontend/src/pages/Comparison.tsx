import { useEffect, useState } from 'react'
import { GitCompare, ArrowRight, CheckCircle, XCircle, Minus } from 'lucide-react'
import { api } from '@/lib/api'
import { RiskGauge } from '@/components/ui/RiskGauge'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { categoryLabel, cn } from '@/lib/utils'
import type { Contract, ComparisonResult } from '@/types'

export function Comparison() {
  const [contracts, setContracts] = useState<Contract[]>([])
  const [idA, setIdA] = useState('')
  const [idB, setIdB] = useState('')
  const [result, setResult] = useState<ComparisonResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [loadingContracts, setLoadingContracts] = useState(true)

  useEffect(() => {
    api.listContracts().then(r => {
      setContracts(r.contracts.filter(c => c.status === 'analyzed'))
      setLoadingContracts(false)
    })
  }, [])

  const compare = async () => {
    if (!idA || !idB) return
    setLoading(true)
    try {
      const res = await api.compareContracts(idA, idB)
      setResult(res)
    } finally {
      setLoading(false)
    }
  }

  if (loadingContracts) return <LoadingSpinner className="mt-20" />

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Contract Comparison</h1>
        <p className="text-gray-500 mt-1">Compare two contracts side-by-side to find the better option.</p>
      </div>

      {/* Selection */}
      <div className="card p-6">
        <div className="grid grid-cols-1 md:grid-cols-[1fr,auto,1fr] gap-4 items-end">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Contract A</label>
            <select value={idA} onChange={e => setIdA(e.target.value)} className="input">
              <option value="">Select contract...</option>
              {contracts.map(c => <option key={c.id} value={c.id}>{c.title}</option>)}
            </select>
          </div>
          <GitCompare className="w-6 h-6 text-gray-400 hidden md:block" />
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Contract B</label>
            <select value={idB} onChange={e => setIdB(e.target.value)} className="input">
              <option value="">Select contract...</option>
              {contracts.filter(c => c.id !== idA).map(c => <option key={c.id} value={c.id}>{c.title}</option>)}
            </select>
          </div>
        </div>
        <button onClick={compare} disabled={!idA || !idB || loading} className="btn-primary mt-4 w-full md:w-auto">
          {loading ? 'Comparing...' : 'Compare Contracts'}
        </button>
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-6">
          {/* Summary */}
          <div className="card p-6">
            <h3 className="font-semibold text-gray-900 mb-3">Comparison Summary</h3>
            <p className="text-gray-700 leading-relaxed">{result.summary}</p>

            <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="flex flex-col items-center">
                <RiskGauge score={result.risk_a * 10} size="sm" />
                <p className="text-sm text-gray-600 mt-2">Contract A</p>
              </div>
              <div className="flex flex-col items-center justify-center">
                <ArrowRight className="w-6 h-6 text-gray-300" />
                <p className={cn('text-sm font-semibold mt-2',
                  result.recommendation === 'A' ? 'text-brand-600' :
                  result.recommendation === 'B' ? 'text-brand-600' : 'text-gray-500'
                )}>
                  {result.recommendation === 'neither'
                    ? 'No clear winner'
                    : `Contract ${result.recommendation} is better`}
                </p>
                <p className="text-xs text-gray-400">{(result.confidence * 100).toFixed(0)}% confidence</p>
              </div>
              <div className="flex flex-col items-center">
                <RiskGauge score={result.risk_b * 10} size="sm" />
                <p className="text-sm text-gray-600 mt-2">Contract B</p>
              </div>
            </div>
          </div>

          {/* Differences */}
          <div className="card">
            <div className="px-6 py-4 border-b border-gray-100">
              <h3 className="font-semibold text-gray-900">Key Differences ({result.differences.length})</h3>
            </div>
            <div className="divide-y divide-gray-100">
              {result.differences.map((diff, i) => (
                <div key={i} className="px-6 py-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-gray-900">{categoryLabel(diff.category)}</span>
                    <div className="flex items-center gap-2">
                      <SignificanceBadge level={diff.significance} />
                      <FavorsBadge favors={diff.favors} />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4 mt-3">
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <p className="text-xs font-medium text-gray-500 mb-1">Contract A</p>
                      <p className="text-sm text-gray-700">{diff.contract_a}</p>
                    </div>
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <p className="text-xs font-medium text-gray-500 mb-1">Contract B</p>
                      <p className="text-sm text-gray-700">{diff.contract_b}</p>
                    </div>
                  </div>
                  <p className="text-sm text-gray-600 mt-2 italic">{diff.impact}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Unchanged */}
          {result.unchanged.length > 0 && (
            <div className="card p-6">
              <h3 className="font-semibold text-gray-900 mb-3">Unchanged Areas</h3>
              <div className="flex flex-wrap gap-2">
                {result.unchanged.map(u => (
                  <span key={u} className="badge bg-gray-100 text-gray-600">{categoryLabel(u)}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function SignificanceBadge({ level }: { level: string }) {
  const styles: Record<string, string> = {
    critical: 'bg-red-100 text-red-700',
    major: 'bg-orange-100 text-orange-700',
    minor: 'bg-yellow-100 text-yellow-700',
    cosmetic: 'bg-gray-100 text-gray-600',
  }
  return <span className={cn('badge', styles[level] ?? styles.minor)}>{level}</span>
}

function FavorsBadge({ favors }: { favors: string }) {
  if (favors === 'A') return <span className="badge bg-blue-100 text-blue-700">Favors A</span>
  if (favors === 'B') return <span className="badge bg-purple-100 text-purple-700">Favors B</span>
  return <span className="badge bg-gray-100 text-gray-500">Neutral</span>
}
