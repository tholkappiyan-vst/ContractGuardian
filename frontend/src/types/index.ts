export interface User {
  id: string
  email: string
  full_name: string
  account_type: 'individual' | 'corporate'
  plan: string
  contracts_used: number
  contracts_limit: number
}

export interface Contract {
  id: string
  title: string
  description: string | null
  contract_type: string | null
  status: 'uploaded' | 'extracting' | 'extracted' | 'analyzing' | 'analyzed' | 'failed'
  language: string
  page_count: number | null
  word_count: number | null
  risk_score: number | null
  uploaded_at: string
  analyzed_at: string | null
}

export interface Clause {
  id: string
  clause_index: number
  section_number: string | null
  title: string | null
  body: string
  category: string
  subcategory: string | null
  confidence: number
  risk_score: number | null
  is_standard: boolean | null
}

export interface Entity {
  id: string
  entity_type: string
  value: string
  original_text: string
  normalized: Record<string, unknown> | null
  confidence: number
  role: string | null
}

export interface RiskScore {
  id: string
  clause_id: string | null
  scope: 'clause' | 'contract' | 'compounding'
  score: number
  label: string
  category: string
  explanation: string
  consequence: string
  affected_party: string | null
  is_standard: boolean | null
  standard_note: string | null
}

export interface Analysis {
  id: string
  version: number
  status: string
  executive_summary: string | null
  contract_type: { type: string; confidence: number } | null
  parties: Array<{ name: string; role: string; type: string }> | null
  dates: Record<string, unknown> | null
  payment_summary: Record<string, unknown> | null
  obligations: { you_must?: string[]; they_must?: string[] } | null
  risk_score: number | null
  risk_label: string | null
  risk_summary: string | null
  top_risks: Array<{ rank: number; summary: string; score: number }> | null
  action_items: { negotiate?: string[]; verify?: string[]; acceptable?: string[] } | null
  processing_ms: number | null
  created_at: string
}

export interface NegotiationSuggestion {
  id: string
  clause_id: string
  difficulty: 'easy' | 'medium' | 'hard'
  label: string
  original_text: string
  alternative_text: string
  explanation: string
  talking_points: string[] | null
  likelihood: string | null
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations: Array<{ clause_id: string; text: string }> | null
  created_at: string
}

export interface ComparisonResult {
  summary: string
  recommendation: 'A' | 'B' | 'neither'
  confidence: number
  risk_a: number
  risk_b: number
  differences: Array<{
    category: string
    significance: string
    contract_a: string
    contract_b: string
    impact: string
    favors: string
  }>
  unchanged: string[]
}
