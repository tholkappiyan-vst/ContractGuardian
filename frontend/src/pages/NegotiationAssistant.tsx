import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Scale, Copy, CheckCircle, MessageSquare, ArrowRight } from 'lucide-react'
import { api } from '@/lib/api'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { cn } from '@/lib/utils'
import type { NegotiationSuggestion } from '@/types'

export function NegotiationAssistant() {
  const { id } = useParams<{ id: string }>()
  const [negotiations, setNegotiations] = useState<NegotiationSuggestion[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [copied, setCopied] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    api.getNegotiations(id).then(r => { setNegotiations(r); setLoading(false) })
  }, [id])

  const copyText = (text: string, itemId: string) => {
    navigator.clipboard.writeText(text)
    setCopied(itemId)
    setTimeout(() => setCopied(null), 2000)
  }

  if (loading) return <LoadingSpinner className="mt-20" />

  if (negotiations.length === 0) {
    return (
      <div className="text-center py-20">
        <CheckCircle className="w-16 h-16 text-green-400 mx-auto mb-4" />
        <h2 className="text-xl font-bold text-gray-900 mb-2">No risky clauses found</h2>
        <p className="text-gray-500">This contract doesn't have clauses risky enough to warrant negotiation suggestions.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
          <Scale className="w-7 h-7 text-brand-600" /> Negotiation Assistant
        </h1>
        <p className="text-gray-500 mt-1">
          Ready-to-use alternative language for risky clauses. Copy and propose to the other party.
        </p>
      </div>

      <div className="space-y-4">
        {negotiations.map(neg => {
          const isExpanded = expandedId === neg.id

          return (
            <div key={neg.id} className="card overflow-hidden">
              {/* Header */}
              <button
                onClick={() => setExpandedId(isExpanded ? null : neg.id)}
                className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 text-left"
              >
                <div className="flex items-center gap-3">
                  <DifficultyDot difficulty={neg.difficulty} />
                  <div>
                    <p className="font-medium text-gray-900">{neg.label}</p>
                    <p className="text-sm text-gray-500">Difficulty: {neg.difficulty} &middot; Likelihood: {neg.likelihood ?? 'unknown'}</p>
                  </div>
                </div>
                <ArrowRight className={cn('w-4 h-4 text-gray-400 transition-transform', isExpanded && 'rotate-90')} />
              </button>

              {/* Expanded content */}
              {isExpanded && (
                <div className="px-6 pb-6 border-t border-gray-100 pt-4 space-y-5">
                  {/* Original */}
                  <div>
                    <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Current Language (Risky)</h4>
                    <div className="p-4 bg-red-50 border border-red-100 rounded-lg">
                      <p className="text-sm text-gray-800 font-mono leading-relaxed">{neg.original_text}</p>
                    </div>
                  </div>

                  {/* Explanation */}
                  <div>
                    <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Why This Is Risky</h4>
                    <p className="text-sm text-gray-700">{neg.explanation}</p>
                  </div>

                  {/* Alternative */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Suggested Alternative</h4>
                      <button
                        onClick={() => copyText(neg.alternative_text, `alt-${neg.id}`)}
                        className="btn-ghost text-xs flex items-center gap-1"
                      >
                        {copied === `alt-${neg.id}` ? <CheckCircle className="w-3 h-3 text-green-500" /> : <Copy className="w-3 h-3" />}
                        {copied === `alt-${neg.id}` ? 'Copied!' : 'Copy'}
                      </button>
                    </div>
                    <div className="p-4 bg-green-50 border border-green-100 rounded-lg">
                      <p className="text-sm text-gray-800 font-mono leading-relaxed">{neg.alternative_text}</p>
                    </div>
                  </div>

                  {/* Talking Points */}
                  {neg.talking_points && neg.talking_points.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-2">
                        <MessageSquare className="w-3 h-3" /> Talking Points
                      </h4>
                      <ul className="space-y-2">
                        {neg.talking_points.map((tp, i) => (
                          <li key={i} className="flex items-start gap-2">
                            <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-brand-400 flex-shrink-0" />
                            <span className="text-sm text-gray-700 italic">"{tp}"</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function DifficultyDot({ difficulty }: { difficulty: string }) {
  const color = difficulty === 'easy' ? 'bg-green-400' : difficulty === 'medium' ? 'bg-yellow-400' : 'bg-red-400'
  return <div className={cn('w-3 h-3 rounded-full', color)} />
}
