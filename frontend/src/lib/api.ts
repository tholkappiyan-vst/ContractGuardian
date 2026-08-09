const BASE = (import.meta.env.VITE_API_URL || '') + '/api/v1'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem('token')
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(err.detail || `Error ${res.status}`)
  }
  return res.json()
}

export const api = {
  // Auth
  register: (data: { email: string; password: string; full_name: string }) =>
    request<{ access_token: string; refresh_token: string }>('/auth/register', {
      method: 'POST', body: JSON.stringify(data),
    }),
  login: (data: { email: string; password: string }) =>
    request<{ access_token: string; refresh_token: string }>('/auth/login', {
      method: 'POST', body: JSON.stringify(data),
    }),
  getMe: () => request<import('@/types').User>('/auth/me'),

  // Contracts
  uploadContract: (formData: FormData) =>
    fetch(`${BASE}/contracts`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      body: formData,
    }).then(async r => {
      if (!r.ok) {
        const err = await r.json().catch(() => ({ detail: 'Upload failed' }))
        throw new Error(err.detail || `Error ${r.status}`)
      }
      return r.json() as Promise<import('@/types').Contract>
    }),
  listContracts: () => request<{ contracts: import('@/types').Contract[]; total: number }>('/contracts'),
  getContract: (id: string) => request<import('@/types').Contract>(`/contracts/${id}`),
  deleteContract: (id: string) => request(`/contracts/${id}`, { method: 'DELETE' }),

  // Analysis
  triggerAnalysis: (id: string) =>
    request<import('@/types').Analysis>(`/analysis/${id}/analyze`, { method: 'POST' }),
  getResults: (id: string) =>
    request<{
      analysis: import('@/types').Analysis
      clauses: import('@/types').Clause[]
      entities: import('@/types').Entity[]
      risks: import('@/types').RiskScore[]
      negotiations: import('@/types').NegotiationSuggestion[]
    }>(`/analysis/${id}/results`),
  getRisks: (id: string) => request<import('@/types').RiskScore[]>(`/analysis/${id}/risks`),
  getClauses: (id: string) => request<import('@/types').Clause[]>(`/analysis/${id}/clauses`),
  getNegotiations: (id: string) =>
    request<import('@/types').NegotiationSuggestion[]>(`/analysis/${id}/negotiations`),

  // Chat
  sendMessage: (contractId: string, message: string) =>
    request<import('@/types').ChatMessage>(`/chat/${contractId}`, {
      method: 'POST', body: JSON.stringify({ message }),
    }),
  getChatHistory: (contractId: string) =>
    request<{ messages: import('@/types').ChatMessage[]; contract_id: string }>(`/chat/${contractId}`),

  // Comparison
  compareContracts: (idA: string, idB: string) =>
    request<import('@/types').ComparisonResult>('/comparison', {
      method: 'POST', body: JSON.stringify({ contract_id_a: idA, contract_id_b: idB }),
    }),

  // Explainability
  explainClause: (contractId: string, clauseId: string) =>
    request<any>(`/explain/${contractId}/clause/${clauseId}`),
  explainClauseQuick: (contractId: string, clauseId: string) =>
    request<any>(`/explain/${contractId}/clause/${clauseId}/quick`),
  explainContract: (contractId: string) =>
    request<any>(`/explain/${contractId}/global`),
  explainBatch: (contractId: string, clauseIds: string[]) =>
    request<any>(`/explain/${contractId}/batch`, {
      method: 'POST', body: JSON.stringify({ clause_ids: clauseIds }),
    }),
}
