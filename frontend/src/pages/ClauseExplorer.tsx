import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { ChevronDown, ChevronRight, Search } from 'lucide-react'
import { api } from '@/lib/api'
import { RiskBadge } from '@/components/ui/RiskBadge'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { categoryLabel } from '@/lib/utils'
import type { Clause } from '@/types'

export function ClauseExplorer() {
  const { id } = useParams<{ id: string }>()
  const [clauses, setClauses] = useState<Clause[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('all')

  useEffect(() => {
    if (!id) return
    api.getClauses(id).then(r => { setClauses(r); setLoading(false) })
  }, [id])

  if (loading) return <LoadingSpinner className="mt-20" />

  const categories = [...new Set(clauses.map(c => c.category))]

  const filtered = clauses.filter(c => {
    if (categoryFilter !== 'all' && c.category !== categoryFilter) return false
    if (search && !c.body.toLowerCase().includes(search.toLowerCase())
      && !(c.title ?? '').toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  const toggle = (clauseId: string) => {
    setExpanded(prev => {
      const next = new Set(prev)
      next.has(clauseId) ? next.delete(clauseId) : next.add(clauseId)
      return next
    })
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Clause Explorer</h1>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text" value={search} onChange={e => setSearch(e.target.value)}
            className="input pl-10" placeholder="Search clauses..."
          />
        </div>
        <select
          value={categoryFilter} onChange={e => setCategoryFilter(e.target.value)}
          className="input w-auto"
        >
          <option value="all">All Categories ({clauses.length})</option>
          {categories.map(cat => (
            <option key={cat} value={cat}>
              {categoryLabel(cat)} ({clauses.filter(c => c.category === cat).length})
            </option>
          ))}
        </select>
      </div>

      {/* Clause List */}
      <div className="space-y-2">
        {filtered.map(clause => {
          const isOpen = expanded.has(clause.id)
          return (
            <div key={clause.id} className="card overflow-hidden">
              <button
                onClick={() => toggle(clause.id)}
                className="w-full px-5 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors text-left"
              >
                <div className="flex items-center gap-3">
                  {isOpen ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
                  <span className="text-xs text-gray-400 font-mono w-8">{clause.section_number ?? `#${clause.clause_index}`}</span>
                  <span className="font-medium text-gray-900">{clause.title ?? categoryLabel(clause.category)}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="badge bg-brand-50 text-brand-700 text-xs">{categoryLabel(clause.category)}</span>
                  {clause.risk_score && <RiskBadge score={clause.risk_score * 10} />}
                  {clause.is_standard && <span className="badge bg-green-50 text-green-700 text-xs">Standard</span>}
                </div>
              </button>

              {isOpen && (
                <div className="px-5 pb-5 border-t border-gray-100 pt-4">
                  <div className="bg-gray-50 rounded-lg p-4 font-mono text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
                    {clause.body}
                  </div>
                  <div className="mt-4 flex items-center gap-4 text-xs text-gray-500">
                    <span>Category: <strong>{categoryLabel(clause.category)}</strong></span>
                    {clause.subcategory && <span>Sub: {clause.subcategory}</span>}
                    <span>Confidence: {(clause.confidence * 100).toFixed(0)}%</span>
                    {clause.risk_score && <span>Risk: {clause.risk_score}/10</span>}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {filtered.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          No clauses match your filters.
        </div>
      )}
    </div>
  )
}
