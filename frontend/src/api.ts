export type TicketStatus =
  | 'open'
  | 'in_progress'
  | 'pending_review'
  | 'resolved'
  | 'escalated'

export type TicketPriority = 'low' | 'medium' | 'high' | 'urgent'

export interface Ticket {
  id: number
  ticket_number: string
  title: string
  description: string
  category: string
  priority: TicketPriority
  assigned_team: string
  status: TicketStatus
  requester_name: string
  requester_email: string
  created_at: string
  updated_at: string
  resolved_at: string | null
}

export interface TicketEvent {
  id: number
  ticket_id: number
  event_type: string
  previous_value: string | null
  new_value: string | null
  actor: string
  timestamp: string
}

export interface TicketListResponse {
  items: Ticket[]
  total: number
  limit: number
  offset: number
}

export interface ResolutionStep {
  text: string
  document_id: string
  source_reference: string
}

export interface SupportingSource {
  document_id: string
  title: string
  category: string
  revision_date: string
  source_reference: string
  chunk_ids: string[]
  retrieval_score: number
  score_type: 'raw_cosine_similarity'
}

export interface TicketSuggestion {
  id: number
  ticket_id: number
  issue_summary: string
  suggested_resolution: string
  approved_resolution: string | null
  evidence_state: 'suggested' | 'insufficient_evidence'
  recommended_steps: ResolutionStep[]
  supporting_sources: SupportingSource[]
  confidence_warning: string
  manual_review_required: boolean
  manual_review_reason: string
  status: 'pending' | 'accepted' | 'edited' | 'rejected'
  reviewer: 'demo-reviewer-1' | 'demo-reviewer-2' | null
  reviewed_at: string | null
  created_at: string
  updated_at: string
}

export interface Analysis {
  predicted_category:
    | 'Hardware'
    | 'Software'
    | 'Network'
    | 'Account & Access'
    | 'Security'
    | 'Other'
  category_confidence: number
  recommended_team: string
  recommended_priority: 'low' | 'medium' | 'high' | 'critical'
  explanation: string
  needs_manual_review: boolean
}

export interface KnowledgeDocument {
  document_id: string
  title: string
  category: string
  revision_date: string
  source_reference: string
}

export interface KnowledgeMatch extends KnowledgeDocument {
  chunk_id: string
  content: string
  similarity_score: number
  score_type: 'raw_cosine_similarity'
}

export interface KnowledgeSearchResponse {
  state: 'reliable_match' | 'no_reliable_match' | 'no_documents'
  matches: KnowledgeMatch[]
  minimum_reliable_score: number
}

export interface AnalyticsSummary {
  total_tickets: number
  open_tickets: number
  resolved_tickets: number
  tickets_by_category: Record<string, number>
  tickets_by_priority: Record<TicketPriority, number>
  tickets_by_status: Record<TicketStatus, number>
  average_resolution_time_seconds: number | null
  average_resolution_time_ticket_count: number
  ai_suggestion_acceptance_rate: number | null
  ai_suggestion_reviewed_count: number
  ai_suggestion_accepted_count: number
  ai_suggestion_edited_count: number
  ai_suggestion_rejected_count: number
}

export interface TicketCreateInput {
  title: string
  description: string
  category: string
  priority: TicketPriority
  requester_name: string
  requester_email: string
  assigned_team?: string
}

export type HumanSupportTeam =
  | 'IT Support'
  | 'Desktop Support'
  | 'Application Support'
  | 'Network Support'
  | 'Identity & Access Support'
  | 'Security Operations'

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

const apiBaseUrl = (
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api'
).replace(/\/+$/, '')

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${apiBaseUrl}${path}`, {
      ...init,
      headers: {
        ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
        ...init?.headers,
      },
    })
  } catch {
    throw new ApiError(
      `Could not connect to ResolveIQ at ${apiBaseUrl}. Check that the backend is running.`,
      0,
    )
  }

  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try {
      const body = (await response.json()) as { detail?: unknown }
      if (typeof body.detail === 'string') {
        message = body.detail
      } else if (Array.isArray(body.detail)) {
        message = body.detail
          .map((item) =>
            typeof item === 'object' &&
            item !== null &&
            'msg' in item &&
            typeof item.msg === 'string'
              ? item.msg
              : 'Invalid request',
          )
          .join('. ')
      }
    } catch {
      // Use the status-based message when the server does not return JSON.
    }
    throw new ApiError(message, response.status)
  }

  return (await response.json()) as T
}

export const api = {
  health: () => request<{ status: string }>('/health'),

  listTickets: (params: {
    limit: number
    offset: number
    search?: string
    status?: string
    category?: string
    priority?: string
  }) => {
    const query = new URLSearchParams({
      limit: String(params.limit),
      offset: String(params.offset),
    })
    for (const key of ['search', 'status', 'category', 'priority'] as const) {
      const value = params[key]
      if (value) query.set(key, value)
    }
    return request<TicketListResponse>(`/tickets?${query.toString()}`)
  },

  getTicket: (id: number) => request<Ticket>(`/tickets/${id}`),

  createTicket: (ticket: TicketCreateInput) =>
    request<Ticket>('/tickets', {
      method: 'POST',
      body: JSON.stringify(ticket),
    }),

  updateStatus: (id: number, status: TicketStatus) =>
    request<Ticket>(`/tickets/${id}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    }),

  ticketHistory: (id: number) =>
    request<TicketEvent[]>(`/tickets/${id}/history`),

  ticketSuggestions: (id: number) =>
    request<TicketSuggestion[]>(`/tickets/${id}/suggestions`),

  createSuggestion: (id: number) =>
    request<TicketSuggestion>(`/tickets/${id}/suggestions`, {
      method: 'POST',
      body: JSON.stringify({ top_k: 3 }),
    }),

  reviewSuggestion: (
    id: number,
    decision: 'accepted' | 'edited' | 'rejected',
    reviewer: 'demo-reviewer-1' | 'demo-reviewer-2',
    editedResolution?: string,
  ) =>
    request<TicketSuggestion>(`/suggestions/${id}/review`, {
      method: 'POST',
      body: JSON.stringify({
        status: decision,
        reviewer,
        ...(editedResolution ? { edited_resolution: editedResolution } : {}),
      }),
    }),

  escalate: (id: number, team: HumanSupportTeam, reason: string) =>
    request<Ticket>(`/tickets/${id}/escalate`, {
      method: 'POST',
      body: JSON.stringify({ team, ...(reason ? { reason } : {}) }),
    }),

  analyzeTicket: (title: string, description: string, businessImpact?: string) =>
    request<Analysis>('/ai/analyze-ticket', {
      method: 'POST',
      body: JSON.stringify({
        title,
        description,
        ...(businessImpact ? { business_impact: businessImpact } : {}),
      }),
    }),

  knowledgeCatalog: () =>
    request<{ items: KnowledgeDocument[]; total: number }>('/knowledge'),

  searchKnowledge: (query: string, topK = 5) =>
    request<KnowledgeSearchResponse>('/knowledge/search', {
      method: 'POST',
      body: JSON.stringify({ query, top_k: topK }),
    }),

  analytics: () => request<AnalyticsSummary>('/analytics/summary'),
}
