import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  GraduationCap, AlertTriangle, HelpCircle, CheckSquare,
  MessageCircle, ChevronDown, ChevronRight, Lightbulb,
  Shield, BookOpen, Eye,
} from 'lucide-react'
import { api } from '@/lib/api'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { cn } from '@/lib/utils'
import type { Analysis, Clause, RiskScore } from '@/types'

// ─────────────────────────────────────────────────────────────────────────────
// LEGAL DICTIONARY — instant tooltips for jargon
// ─────────────────────────────────────────────────────────────────────────────

const LEGAL_DICTIONARY: Record<string, { simple: string; example: string }> = {
  'indemnification': {
    simple: 'You may have to pay money if your actions cause damage to the other party.',
    example: 'If you accidentally break their equipment, you pay for it — even if it was an honest mistake.',
  },
  'indemnify': {
    simple: 'Promise to cover someone else\'s losses or legal costs.',
    example: 'If they get sued because of your work, you pay their lawyer bills.',
  },
  'liability': {
    simple: 'Legal responsibility — who pays when something goes wrong.',
    example: 'If the project fails and costs them money, liability decides whether YOU owe them.',
  },
  'liquidated damages': {
    simple: 'A pre-agreed penalty amount you pay if you break the contract.',
    example: 'Miss a deadline? You owe $500 per day — no argument, it\'s already decided.',
  },
  'force majeure': {
    simple: 'Events nobody can control (earthquakes, wars, pandemics) that excuse both sides.',
    example: 'If a hurricane shuts everything down, neither side gets penalized.',
  },
  'non-compete': {
    simple: 'You can\'t work for a competitor for a certain time after leaving.',
    example: 'Leave this job? You can\'t work at a similar company for 2 years.',
  },
  'non-solicitation': {
    simple: 'You can\'t recruit their employees or steal their clients after leaving.',
    example: 'You can\'t call their customers and say "come work with me instead."',
  },
  'termination for cause': {
    simple: 'They can fire you / end the contract if you do something wrong.',
    example: 'If you violate a rule, they can end this immediately — no notice needed.',
  },
  'termination for convenience': {
    simple: 'They can end the contract for any reason, even if you did nothing wrong.',
    example: 'They just changed their mind. They give you 30 days notice and walk away.',
  },
  'severability': {
    simple: 'If one part of the contract is illegal, the rest still counts.',
    example: 'A judge strikes out one clause? Everything else stays in effect.',
  },
  'governing law': {
    simple: 'Which state\'s or country\'s laws apply if there\'s a dispute.',
    example: 'If you disagree, a court in California decides — even if you live in Texas.',
  },
  'arbitration': {
    simple: 'Disputes go to a private judge (arbitrator) instead of a regular court.',
    example: 'No jury, no public trial. A hired arbitrator decides. Usually faster, but harder to appeal.',
  },
  'waiver': {
    simple: 'Giving up a right you normally have.',
    example: 'You waive your right to sue — meaning you can\'t take them to court.',
  },
  'assignment': {
    simple: 'Transferring your contract rights/duties to someone else.',
    example: 'They sell their company? Your contract might transfer to the new owner without asking you.',
  },
  'intellectual property': {
    simple: 'Creations of your mind — code, designs, writing, inventions.',
    example: 'That app you build at work? The company owns it, not you.',
  },
  'work for hire': {
    simple: 'Anything you create during work belongs to them automatically.',
    example: 'You write code on their time? They own it from the moment you type it.',
  },
  'confidentiality': {
    simple: 'You must keep their secrets. Breaking this has serious consequences.',
    example: 'You can\'t tell friends, family, or your next employer about their business plans.',
  },
  'material breach': {
    simple: 'A serious violation that breaks the core deal.',
    example: 'Not a typo in a report — but failing to deliver the main thing you promised.',
  },
  'representations and warranties': {
    simple: 'Promises that certain facts are true. If they\'re not, you\'re in trouble.',
    example: '"I confirm I have the legal right to do this work." If you don\'t, you lied — that\'s a breach.',
  },
}

// ─────────────────────────────────────────────────────────────────────────────
// SIGNING CHECKLIST — universal questions before signing ANY contract
// ─────────────────────────────────────────────────────────────────────────────

interface ChecklistItem {
  id: string
  question: string
  why: string
  category: 'understand' | 'negotiate' | 'protect'
}

const SIGNING_CHECKLIST: ChecklistItem[] = [
  { id: 'read', question: 'Have I read the ENTIRE contract?', why: 'The worst clauses are often buried at the end.', category: 'understand' },
  { id: 'understand', question: 'Do I understand every clause?', why: 'If you can\'t explain it to a friend, you don\'t understand it.', category: 'understand' },
  { id: 'term', question: 'Do I know exactly when this contract ends?', why: 'Auto-renewal traps can lock you in for years.', category: 'understand' },
  { id: 'termination', question: 'Can I get out of this if I need to?', why: 'Know the exit before you enter.', category: 'understand' },
  { id: 'cost', question: 'Do I know the total cost — including hidden fees and penalties?', why: 'Late fees, early termination fees, and penalty clauses add up.', category: 'understand' },
  { id: 'liability', question: 'Is my financial risk capped?', why: 'Without a cap, one mistake could cost you everything.', category: 'negotiate' },
  { id: 'noncompete', question: 'Can I still work in my field after this ends?', why: 'Non-compete clauses can block your career for years.', category: 'negotiate' },
  { id: 'ip', question: 'Do I keep ownership of my pre-existing work?', why: 'Broad IP clauses can claim things you created before this job.', category: 'negotiate' },
  { id: 'changes', question: 'Can they change terms without my agreement?', why: 'Unilateral amendment clauses let them rewrite the deal later.', category: 'protect' },
  { id: 'dispute', question: 'Do I know how disputes are resolved?', why: 'Arbitration in a different state could make it impossible to fight back.', category: 'protect' },
  { id: 'copy', question: 'Do I have my own signed copy?', why: 'Always keep your own copy. They can\'t deny what\'s in writing.', category: 'protect' },
]

// ─────────────────────────────────────────────────────────────────────────────
// QUESTIONS TO ASK THE COMPANY
// ─────────────────────────────────────────────────────────────────────────────

interface QuestionToAsk {
  question: string
  context: string
  when: string
}

const QUESTIONS_TO_ASK: QuestionToAsk[] = [
  { question: 'Is there any flexibility on the non-compete clause?', context: 'Non-competes restrict where you can work after leaving.', when: 'If you see a non-compete' },
  { question: 'Can we add a liability cap?', context: 'Without one, you could owe unlimited damages.', when: 'If there\'s no liability limit' },
  { question: 'What happens if I need to leave early?', context: 'Know the cost of exiting before you commit.', when: 'Always' },
  { question: 'Can I get this reviewed by my own lawyer first?', context: 'Legitimate companies never pressure you to sign immediately.', when: 'Always' },
  { question: 'Are there any penalties I should know about?', context: 'Late fees, clawbacks, and liquidated damages can surprise you.', when: 'Always' },
  { question: 'Who owns work I create in my personal time?', context: 'Some contracts claim everything you create — even on weekends.', when: 'If broad IP assignment exists' },
  { question: 'Can I see the last version of changes tracked?', context: 'Compare what changed between drafts. Things disappear quietly.', when: 'If they send a "revised" version' },
  { question: 'What does "reasonable" mean specifically?', context: 'Vague words like "reasonable efforts" mean whatever a court decides later.', when: 'If you see vague obligations' },
]

// ─────────────────────────────────────────────────────────────────────────────
// COMPONENT
// ─────────────────────────────────────────────────────────────────────────────

export function BeginnerMode() {
  const { id } = useParams<{ id: string }>()
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [clauses, setClauses] = useState<Clause[]>([])
  const [risks, setRisks] = useState<RiskScore[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'overview' | 'clauses' | 'checklist' | 'questions'>('overview')
  const [checkedItems, setCheckedItems] = useState<Set<string>>(new Set())
  const [expandedClause, setExpandedClause] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    api.getResults(id).then(r => {
      setAnalysis(r.analysis)
      setClauses(r.clauses)
      setRisks(r.risks)
      setLoading(false)
    })
  }, [id])

  if (loading) return <LoadingSpinner className="mt-20" />
  if (!analysis) return <p>Analysis not found</p>

  const dangerClauses = clauses.filter(c => (c.risk_score ?? 0) >= 7)
  const warningClauses = clauses.filter(c => (c.risk_score ?? 0) >= 4 && (c.risk_score ?? 0) < 7)
  const safeClauses = clauses.filter(c => (c.risk_score ?? 0) < 4)

  const tabs = [
    { key: 'overview', label: 'Simple Summary', icon: BookOpen },
    { key: 'clauses', label: 'What Each Part Means', icon: Eye },
    { key: 'checklist', label: 'Before You Sign', icon: CheckSquare },
    { key: 'questions', label: 'Questions to Ask', icon: MessageCircle },
  ] as const

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-purple-100 rounded-xl flex items-center justify-center">
          <GraduationCap className="w-6 h-6 text-purple-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Beginner Mode</h1>
          <p className="text-gray-500 text-sm">Everything explained in plain language — no legal background needed.</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-xl">
        {tabs.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={cn(
              'flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors flex-1 justify-center',
              activeTab === key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            )}
          >
            <Icon className="w-4 h-4" /> {label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <OverviewTab
          analysis={analysis}
          dangerCount={dangerClauses.length}
          warningCount={warningClauses.length}
          safeCount={safeClauses.length}
        />
      )}
      {activeTab === 'clauses' && (
        <ClausesTab
          clauses={clauses}
          risks={risks}
          expandedClause={expandedClause}
          setExpandedClause={setExpandedClause}
        />
      )}
      {activeTab === 'checklist' && (
        <ChecklistTab checked={checkedItems} setChecked={setCheckedItems} />
      )}
      {activeTab === 'questions' && (
        <QuestionsTab clauses={clauses} />
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// TAB: OVERVIEW
// ─────────────────────────────────────────────────────────────────────────────

function OverviewTab({ analysis, dangerCount, warningCount, safeCount }: {
  analysis: Analysis; dangerCount: number; warningCount: number; safeCount: number
}) {
  const score = (analysis.risk_score ?? 5) * 10
  const emoji = score <= 30 ? '✅' : score <= 60 ? '⚠️' : '🚨'
  const verdict = score <= 30
    ? 'This contract looks fairly safe. Standard terms, no major red flags.'
    : score <= 60
    ? 'This contract has some concerns. Read carefully before signing.'
    : 'This contract has serious risks. Do NOT sign without changes or legal advice.'

  return (
    <div className="space-y-6">
      {/* Big verdict */}
      <div className={cn('card p-8 text-center', score > 60 ? 'bg-red-50 border-red-200' : score > 30 ? 'bg-yellow-50 border-yellow-200' : 'bg-green-50 border-green-200')}>
        <p className="text-4xl mb-3">{emoji}</p>
        <h2 className="text-xl font-bold text-gray-900 mb-2">
          {score <= 30 ? 'Looks Good' : score <= 60 ? 'Be Careful' : 'Danger — Read Closely'}
        </h2>
        <p className="text-gray-700 max-w-lg mx-auto">{verdict}</p>
      </div>

      {/* Traffic light summary */}
      <div className="grid grid-cols-3 gap-4">
        <TrafficLight color="red" count={dangerCount} label="Dangerous" desc="Must negotiate or get advice" />
        <TrafficLight color="yellow" count={warningCount} label="Warning" desc="Read carefully, consider negotiating" />
        <TrafficLight color="green" count={safeCount} label="Safe" desc="Standard terms, no concern" />
      </div>

      {/* Plain summary */}
      {analysis.executive_summary && (
        <div className="card p-6">
          <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-brand-600" /> In Plain English
          </h3>
          <p className="text-gray-700 leading-relaxed text-lg">{analysis.executive_summary}</p>
        </div>
      )}

      {/* What you're agreeing to */}
      {analysis.obligations && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="card p-6">
            <h3 className="font-semibold text-gray-900 mb-3">What YOU must do:</h3>
            <ul className="space-y-2">
              {(analysis.obligations.you_must ?? []).map((item, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                  <span className="mt-1 w-2 h-2 rounded-full bg-blue-400 flex-shrink-0" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
          <div className="card p-6">
            <h3 className="font-semibold text-gray-900 mb-3">What THEY must do:</h3>
            <ul className="space-y-2">
              {(analysis.obligations.they_must ?? []).map((item, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                  <span className="mt-1 w-2 h-2 rounded-full bg-green-400 flex-shrink-0" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}

function TrafficLight({ color, count, label, desc }: {
  color: 'red' | 'yellow' | 'green'; count: number; label: string; desc: string
}) {
  const styles = {
    red: 'border-red-200 bg-red-50',
    yellow: 'border-yellow-200 bg-yellow-50',
    green: 'border-green-200 bg-green-50',
  }
  const dotColor = { red: 'bg-red-500', yellow: 'bg-yellow-500', green: 'bg-green-500' }

  return (
    <div className={cn('card p-5 border', styles[color])}>
      <div className="flex items-center gap-3 mb-2">
        <div className={cn('w-4 h-4 rounded-full', dotColor[color])} />
        <span className="text-2xl font-bold text-gray-900">{count}</span>
      </div>
      <p className="font-medium text-gray-900">{label}</p>
      <p className="text-xs text-gray-600 mt-1">{desc}</p>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// TAB: CLAUSES (with legal word explanations)
// ─────────────────────────────────────────────────────────────────────────────

function ClausesTab({ clauses, risks, expandedClause, setExpandedClause }: {
  clauses: Clause[]; risks: RiskScore[]; expandedClause: string | null; setExpandedClause: (id: string | null) => void
}) {
  const sorted = [...clauses].sort((a, b) => (b.risk_score ?? 0) - (a.risk_score ?? 0))

  return (
    <div className="space-y-3">
      <p className="text-sm text-gray-500 flex items-center gap-2">
        <Lightbulb className="w-4 h-4 text-yellow-500" />
        Clauses are sorted by risk. Most dangerous first. Tap any legal word highlighted in
        <span className="px-1.5 py-0.5 bg-purple-100 text-purple-700 rounded text-xs font-medium">purple</span>
        for a plain explanation.
      </p>

      {sorted.map(clause => {
        const isOpen = expandedClause === clause.id
        const risk = risks.find(r => r.clause_id === clause.id && r.scope === 'clause')
        const riskLevel = clause.risk_score ?? 0
        const borderColor = riskLevel >= 7 ? 'border-l-red-500' : riskLevel >= 4 ? 'border-l-yellow-500' : 'border-l-green-500'

        return (
          <div key={clause.id} className={cn('card border-l-4 overflow-hidden', borderColor)}>
            <button
              onClick={() => setExpandedClause(isOpen ? null : clause.id)}
              className="w-full px-5 py-4 flex items-center justify-between text-left hover:bg-gray-50"
            >
              <div className="flex items-center gap-3">
                <DangerIcon level={riskLevel} />
                <div>
                  <p className="font-medium text-gray-900">{clause.title ?? `Clause ${clause.clause_index + 1}`}</p>
                  <p className="text-xs text-gray-500">{clauseCategory(clause.category)}</p>
                </div>
              </div>
              {isOpen ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
            </button>

            {isOpen && (
              <div className="px-5 pb-5 space-y-4 border-t border-gray-100 pt-4">
                {/* Original text with highlighted legal terms */}
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Original Contract Language</p>
                  <div className="p-4 bg-gray-50 rounded-lg text-sm text-gray-700 leading-relaxed">
                    <HighlightedText text={clause.body} />
                  </div>
                </div>

                {/* Risk explanation */}
                {risk && (
                  <div className={cn('p-4 rounded-lg', riskLevel >= 7 ? 'bg-red-50' : riskLevel >= 4 ? 'bg-yellow-50' : 'bg-green-50')}>
                    <p className="text-xs font-semibold uppercase mb-1 text-gray-500">What this means for you</p>
                    <p className="text-sm text-gray-800 font-medium">{risk.explanation}</p>
                    {risk.consequence && (
                      <p className="text-sm text-gray-600 mt-2 italic">Worst case: {risk.consequence}</p>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

function HighlightedText({ text }: { text: string }) {
  const terms = Object.keys(LEGAL_DICTIONARY)
  const regex = new RegExp(`\\b(${terms.join('|')})\\b`, 'gi')
  const parts = text.split(regex)

  const [tooltip, setTooltip] = useState<string | null>(null)

  return (
    <span>
      {parts.map((part, i) => {
        const lower = part.toLowerCase()
        const def = LEGAL_DICTIONARY[lower]
        if (def) {
          return (
            <span key={i} className="relative inline">
              <button
                onClick={() => setTooltip(tooltip === lower ? null : lower)}
                className="px-1 py-0.5 bg-purple-100 text-purple-800 rounded font-medium hover:bg-purple-200 transition-colors"
              >
                {part}
              </button>
              {tooltip === lower && (
                <span className="absolute left-0 top-full mt-1 z-10 w-72 p-3 bg-white border border-gray-200 rounded-lg shadow-lg text-left">
                  <span className="block text-sm font-semibold text-gray-900 mb-1">"{part}"</span>
                  <span className="block text-sm text-gray-700 mb-2">{def.simple}</span>
                  <span className="block text-xs text-gray-500 italic">Example: {def.example}</span>
                </span>
              )}
            </span>
          )
        }
        return <span key={i}>{part}</span>
      })}
    </span>
  )
}

function DangerIcon({ level }: { level: number }) {
  if (level >= 7) return <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center"><AlertTriangle className="w-4 h-4 text-red-600" /></div>
  if (level >= 4) return <div className="w-8 h-8 bg-yellow-100 rounded-full flex items-center justify-center"><HelpCircle className="w-4 h-4 text-yellow-600" /></div>
  return <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center"><Shield className="w-4 h-4 text-green-600" /></div>
}

function clauseCategory(cat: string): string {
  const map: Record<string, string> = {
    payment: '💰 Money & Payment',
    termination: '🚪 Ending the Contract',
    liability: '⚖️ Who Pays If Something Goes Wrong',
    confidentiality: '🤫 Keeping Secrets',
    ip_rights: '💡 Who Owns Your Work',
    data_privacy: '🔒 Your Personal Data',
    non_compete: '🚫 Where You Can Work After',
    warranty: '✋ Promises & Guarantees',
    dispute_resolution: '🏛️ How Fights Are Settled',
    penalties: '💸 Fines & Penalties',
  }
  return map[cat] ?? cat
}

// ─────────────────────────────────────────────────────────────────────────────
// TAB: SIGNING CHECKLIST
// ─────────────────────────────────────────────────────────────────────────────

function ChecklistTab({ checked, setChecked }: {
  checked: Set<string>; setChecked: (s: Set<string>) => void
}) {
  const toggle = (id: string) => {
    const next = new Set(checked)
    next.has(id) ? next.delete(id) : next.add(id)
    setChecked(next)
  }

  const progress = Math.round((checked.size / SIGNING_CHECKLIST.length) * 100)
  const categories = {
    understand: { label: 'Do You Understand?', icon: BookOpen },
    negotiate: { label: 'Should You Negotiate?', icon: MessageCircle },
    protect: { label: 'Are You Protected?', icon: Shield },
  }

  return (
    <div className="space-y-6">
      {/* Progress bar */}
      <div className="card p-5">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">Signing Readiness</span>
          <span className="text-sm font-bold text-gray-900">{checked.size}/{SIGNING_CHECKLIST.length}</span>
        </div>
        <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={cn('h-full rounded-full transition-all', progress === 100 ? 'bg-green-500' : 'bg-brand-500')}
            style={{ width: `${progress}%` }}
          />
        </div>
        {progress === 100 && (
          <p className="text-sm text-green-700 font-medium mt-2 flex items-center gap-2">
            <CheckSquare className="w-4 h-4" /> You've verified everything. Ready to sign (if comfortable).
          </p>
        )}
      </div>

      {/* Grouped checklist */}
      {(Object.entries(categories) as [string, { label: string; icon: typeof BookOpen }][]).map(([key, { label, icon: Icon }]) => (
        <div key={key} className="card">
          <div className="px-5 py-3 bg-gray-50 border-b border-gray-100 flex items-center gap-2">
            <Icon className="w-4 h-4 text-gray-500" />
            <span className="font-medium text-gray-700 text-sm">{label}</span>
          </div>
          <div className="divide-y divide-gray-100">
            {SIGNING_CHECKLIST.filter(i => i.category === key).map(item => (
              <label key={item.id} className="flex items-start gap-3 px-5 py-4 cursor-pointer hover:bg-gray-50">
                <input
                  type="checkbox"
                  checked={checked.has(item.id)}
                  onChange={() => toggle(item.id)}
                  className="mt-0.5 w-5 h-5 rounded border-gray-300 text-brand-600 focus:ring-brand-500"
                />
                <div>
                  <p className={cn('text-sm font-medium', checked.has(item.id) ? 'text-gray-400 line-through' : 'text-gray-900')}>
                    {item.question}
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5">{item.why}</p>
                </div>
              </label>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// TAB: QUESTIONS TO ASK
// ─────────────────────────────────────────────────────────────────────────────

function QuestionsTab({ clauses }: { clauses: Clause[] }) {
  const hasNonCompete = clauses.some(c => c.category === 'non_compete')
  const hasNoLiabilityCap = clauses.some(c => c.category === 'liability' && (c.risk_score ?? 0) >= 7)
  const hasBroadIP = clauses.some(c => c.category === 'ip_rights' && (c.risk_score ?? 0) >= 6)

  const relevant = QUESTIONS_TO_ASK.filter(q => {
    if (q.when === 'Always') return true
    if (q.when === 'If you see a non-compete' && hasNonCompete) return true
    if (q.when === 'If there\'s no liability limit' && hasNoLiabilityCap) return true
    if (q.when === 'If broad IP assignment exists' && hasBroadIP) return true
    if (q.when === 'If they send a "revised" version') return true
    if (q.when === 'If you see vague obligations') return true
    return false
  })

  return (
    <div className="space-y-4">
      <div className="card p-5 bg-blue-50 border-blue-200">
        <p className="text-sm text-blue-800">
          <strong>Tip:</strong> Asking questions is normal and expected. If they pressure you NOT to ask, that's a red flag.
          Good companies want you to understand what you're signing.
        </p>
      </div>

      {relevant.map((q, i) => (
        <div key={i} className="card p-5">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 bg-brand-50 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
              <MessageCircle className="w-4 h-4 text-brand-600" />
            </div>
            <div>
              <p className="font-medium text-gray-900 text-lg">"{q.question}"</p>
              <p className="text-sm text-gray-600 mt-1">{q.context}</p>
              <p className="text-xs text-gray-400 mt-2">Ask when: {q.when}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
