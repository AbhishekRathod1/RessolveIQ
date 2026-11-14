import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  ArrowUpRight,
  Bot,
  Check,
  CheckCircle2,
  Clock3,
  FileText,
  LoaderCircle,
  Pencil,
  RefreshCw,
  ShieldAlert,
  Sparkles,
  X,
} from 'lucide-react'

import {
  api,
  type Analysis,
  type HumanSupportTeam,
  type Ticket,
  type TicketEvent,
  type TicketStatus,
  type TicketSuggestion,
} from '../api'
import {
  Button,
  Card,
  EmptyState,
  ErrorInline,
  ErrorState,
  LoadingState,
  PageHeader,
  PriorityPill,
  SectionTitle,
  StatusPill,
} from '../components'
import { formatCategory, formatDate } from '../utils'

const teams: HumanSupportTeam[] = [
  'IT Support',
  'Desktop Support',
  'Application Support',
  'Network Support',
  'Identity & Access Support',
  'Security Operations',
]

const nextStatuses: Record<TicketStatus, TicketStatus[]> = {
  open: ['in_progress', 'escalated'],
  in_progress: ['open', 'pending_review', 'resolved', 'escalated'],
  pending_review: ['in_progress', 'resolved', 'escalated'],
  escalated: ['in_progress', 'pending_review', 'resolved'],
  resolved: [],
}

const eventLabels: Record<string, string> = {
  created: 'Ticket created',
  status_changed: 'Status changed',
  assigned_team_changed: 'Team reassigned',
  ticket_escalated: 'Ticket escalated',
  suggestion_created: 'AI suggestion generated',
  suggestion_accepted: 'Suggestion accepted',
  suggestion_edited: 'Suggestion edited',
  suggestion_rejected: 'Suggestion rejected',
  title_changed: 'Title updated',
  description_changed: 'Description updated',
  category_changed: 'Category updated',
  priority_changed: 'Priority updated',
  requester_name_changed: 'Requester updated',
  requester_email_changed: 'Requester email updated',
}

function getTicketData(ticketId: number) {
  if (!Number.isInteger(ticketId) || ticketId < 1) {
    return Promise.reject(new Error('This ticket ID is not valid.'))
  }
  return Promise.all([
    api.getTicket(ticketId),
    api.ticketSuggestions(ticketId),
    api.ticketHistory(ticketId),
  ] as const)
}

function readableValue(value: string | null) {
  if (!value) return ''
  try {
    const parsed: unknown = JSON.parse(value)
    if (typeof parsed === 'object' && parsed !== null) {
      return Object.entries(parsed)
        .map(([key, item]) => `${key.replaceAll('_', ' ')}: ${String(item)}`)
        .join(' · ')
    }
  } catch {
    return value.replaceAll('_', ' ')
  }
  return value
}

export function TicketDetailsPage() {
  const { id } = useParams()
  const ticketId = Number(id)
  const [ticket, setTicket] = useState<Ticket | null>(null)
  const [suggestions, setSuggestions] = useState<TicketSuggestion[]>([])
  const [history, setHistory] = useState<TicketEvent[]>([])
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [analysisError, setAnalysisError] = useState('')
  const [analysisLoading, setAnalysisLoading] = useState(true)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [actionError, setActionError] = useState('')
  const [actionSuccess, setActionSuccess] = useState('')
  const [working, setWorking] = useState(false)
  const [nextStatus, setNextStatus] = useState<TicketStatus | ''>('')
  const [escalationTeam, setEscalationTeam] =
    useState<HumanSupportTeam>('IT Support')
  const [escalationReason, setEscalationReason] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editedResolution, setEditedResolution] = useState('')

  const applyTicketData = useCallback((
    [ticketData, suggestionData, historyData]: Awaited<
      ReturnType<typeof getTicketData>
    >,
  ) => {
    setAnalysis(null)
    setAnalysisError('')
    setAnalysisLoading(true)
    setTicket(ticketData)
    setSuggestions(suggestionData)
    setHistory(historyData)
    setNextStatus('')
  }, [])

  const load = useCallback(async (showLoading = false): Promise<boolean> => {
    if (showLoading) {
      setLoading(true)
    }
    setError('')
    try {
      applyTicketData(await getTicketData(ticketId))
      return true
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : 'Ticket details failed to load.')
      return false
    } finally {
      setLoading(false)
    }
  }, [applyTicketData, ticketId])

  useEffect(() => {
    let active = true
    void getTicketData(ticketId).then(
      (data) => {
        if (active) applyTicketData(data)
      },
      (issue: unknown) => {
        if (active) {
          setError(
            issue instanceof Error
              ? issue.message
              : 'Ticket details failed to load.',
          )
        }
      },
    ).finally(() => {
      if (active) setLoading(false)
    })
    return () => {
      active = false
    }
  }, [applyTicketData, ticketId])

  useEffect(() => {
    if (!ticket) return
    let active = true
    void api.analyzeTicket(ticket.title, ticket.description).then(
      (result) => {
        if (active) setAnalysis(result)
      },
      (issue: unknown) => {
        if (active) {
          setAnalysisError(
            issue instanceof Error ? issue.message : 'AI analysis is unavailable.',
          )
        }
      },
    ).finally(() => {
      if (active) setAnalysisLoading(false)
    })
    return () => {
      active = false
    }
  }, [ticket])

  if (!Number.isInteger(ticketId) || ticketId < 1) {
    return <ErrorState message="This ticket ID is not valid." />
  }

  async function performAction(
    successMessage: string,
    action: () => Promise<unknown>,
  ) {
    setWorking(true)
    setActionError('')
    setActionSuccess('')
    try {
      await action()
      if (await load()) {
        setActionSuccess(successMessage)
      } else {
        setActionError('The action was saved, but the latest ticket data could not be refreshed.')
      }
    } catch (issue) {
      setActionError(
        issue instanceof Error ? issue.message : 'The requested action could not be completed.',
      )
    } finally {
      setWorking(false)
    }
  }

  async function changeStatus() {
    if (!nextStatus) return
    await performAction(`Ticket status updated to ${nextStatus.replaceAll('_', ' ')}.`, async () => {
      await api.updateStatus(ticketId, nextStatus)
    })
  }

  async function generateSuggestion() {
    await performAction('Knowledge suggestion saved and ready for human review.', async () => {
      await api.createSuggestion(ticketId)
    })
  }

  async function reviewSuggestion(
    suggestion: TicketSuggestion,
    decision: 'accepted' | 'edited' | 'rejected',
  ) {
    const successMessage =
      decision === 'edited'
        ? 'Edited resolution approved and saved.'
        : `Suggestion ${decision}.`
    await performAction(successMessage, async () => {
      await api.reviewSuggestion(
        suggestion.id,
        decision,
        'demo-reviewer-1',
        decision === 'edited' ? editedResolution : undefined,
      )
      setEditingId(null)
      setEditedResolution('')
    })
  }

  async function escalateTicket() {
    await performAction(`Ticket escalated to ${escalationTeam}.`, async () => {
      await api.escalate(ticketId, escalationTeam, escalationReason.trim())
      setEscalationReason('')
    })
  }

  async function retryAnalysis() {
    if (!ticket) return
    setAnalysisLoading(true)
    setAnalysisError('')
    try {
      setAnalysis(await api.analyzeTicket(ticket.title, ticket.description))
    } catch (issue) {
      setAnalysisError(
        issue instanceof Error ? issue.message : 'AI analysis is unavailable.',
      )
    } finally {
      setAnalysisLoading(false)
    }
  }

  async function retryTicketLoad() {
    if (await load(true)) setActionError('')
  }

  if (loading) return <LoadingState label="Loading ticket details" />
  if (error || !ticket) {
    const message = actionError ? `${actionError} ${error}` : error || 'Ticket not found.'
    return (
      <ErrorState
        message={message}
        onRetry={() => void retryTicketLoad()}
      />
    )
  }

  const canEscalate = ticket.status !== 'resolved' && ticket.status !== 'escalated'
  const resolutionHint =
    ticket.status === 'resolved'
      ? 'This ticket is resolved.'
      : 'Changing status does not approve or apply an AI suggestion.'

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow={ticket.ticket_number}
        title={ticket.title}
        description={`Created ${formatDate(ticket.created_at, true)} by ${ticket.requester_name}`}
        action={
          <div className="header-action-row">
            <Link to="/tickets" className="button button-ghost">
              <ArrowLeft size={16} /> All tickets
            </Link>
            <Button
              variant="secondary"
              onClick={() => void load(true)}
              disabled={working}
              title="Refresh ticket data"
            >
              <RefreshCw size={15} /> Refresh
            </Button>
          </div>
        }
      />

      {actionError && <ErrorInline message={actionError} />}
      {actionSuccess && (
        <p className="success-banner" role="status">
          <CheckCircle2 size={16} />
          {actionSuccess}
        </p>
      )}
      <div className="ticket-detail-grid">
        <div className="ticket-detail-main">
          <Card className="ticket-overview-card">
            <SectionTitle
              title="Ticket overview"
              subtitle="Request details and current assignment"
              action={<StatusPill status={ticket.status} />}
            />
            <div className="ticket-description">{ticket.description}</div>
            <div className="ticket-facts-grid">
              <div className="ticket-fact">
                <span>Category</span>
                <strong>{formatCategory(ticket.category)}</strong>
              </div>
              <div className="ticket-fact">
                <span>Priority</span>
                <PriorityPill priority={ticket.priority} />
              </div>
              <div className="ticket-fact">
                <span>Assigned team</span>
                <strong>{ticket.assigned_team}</strong>
              </div>
              <div className="ticket-fact">
                <span>Requester</span>
                <strong>{ticket.requester_name}</strong>
                <small>{ticket.requester_email}</small>
              </div>
              <div className="ticket-fact">
                <span>Last updated</span>
                <strong>{formatDate(ticket.updated_at, true)}</strong>
              </div>
              <div className="ticket-fact">
                <span>Resolved at</span>
                <strong>{ticket.resolved_at ? formatDate(ticket.resolved_at, true) : 'Not resolved'}</strong>
              </div>
            </div>
          </Card>

          <Card className="analysis-card">
            <SectionTitle
              title="AI triage recommendation"
              subtitle="A non-binding recommendation from the ticket classifier"
              action={<span className="ai-small-tag"><Sparkles size={13} /> DEMO AI</span>}
            />
            {analysisError ? (
              <div>
                <ErrorInline message={analysisError} />
                <Button
                  variant="secondary"
                  className="mt-3"
                  onClick={() => void retryAnalysis()}
                  disabled={analysisLoading}
                >
                  {analysisLoading ? (
                    <LoaderCircle className="animate-spin" size={15} />
                  ) : (
                    <RefreshCw size={15} />
                  )}
                  Retry analysis
                </Button>
              </div>
            ) : !analysis ? (
              <LoadingState label={analysisLoading ? 'Analyzing ticket' : 'No analysis available'} />
            ) : (
              <>
                <div className="triage-grid">
                  <div className="triage-item">
                    <span>Recommended category</span>
                    <strong>{analysis.predicted_category}</strong>
                  </div>
                  <div className="triage-item">
                    <span>Classifier confidence</span>
                    <strong>{(analysis.category_confidence * 100).toFixed(1)}%</strong>
                  </div>
                  <div className="triage-item">
                    <span>Priority rule</span>
                    <PriorityPill
                      priority={
                        analysis.recommended_priority === 'critical'
                          ? 'urgent'
                          : analysis.recommended_priority
                      }
                    />
                  </div>
                  <div className="triage-item">
                    <span>Suggested team</span>
                    <strong>{analysis.recommended_team}</strong>
                  </div>
                </div>
                <p className="analysis-explanation">{analysis.explanation}</p>
                {analysis.needs_manual_review && (
                  <p className="review-warning">
                    <ShieldAlert size={16} />
                    Low-confidence classification. Please verify before acting.
                  </p>
                )}
              </>
            )}
          </Card>

          <Card className="suggestions-card">
            <SectionTitle
              title="Knowledge suggestions"
              subtitle="Evidence-based guidance for a human to review"
              action={
                <Button
                  variant="secondary"
                  onClick={() => void generateSuggestion()}
                  disabled={working}
                >
                  {working ? (
                    <LoaderCircle className="animate-spin" size={15} />
                  ) : (
                    <Sparkles size={15} />
                  )}
                  Generate suggestion
                </Button>
              }
            />
            {suggestions.length === 0 ? (
              <EmptyState
                title="No suggestions yet"
                description="Generate a knowledge-based suggestion. Every suggestion requires human review."
                icon="check"
              />
            ) : (
              <div className="suggestion-list">
                {suggestions.map((suggestion) => (
                  <article className="suggestion-item" key={suggestion.id}>
                    <div className="suggestion-item-header">
                      <span className="suggestion-icon"><Bot size={17} /></span>
                      <div className="suggestion-heading">
                        <div>
                          <strong>Resolution suggestion</strong>
                          <span className={`suggestion-status suggestion-${suggestion.status}`}>
                            {suggestion.status.replaceAll('_', ' ')}
                          </span>
                        </div>
                        <small>Created {formatDate(suggestion.created_at, true)}</small>
                      </div>
                      {suggestion.evidence_state === 'suggested' ? (
                        <span className="evidence-good"><CheckCircle2 size={14} /> Evidence found</span>
                      ) : (
                        <span className="evidence-weak"><ShieldAlert size={14} /> Insufficient evidence</span>
                      )}
                    </div>
                    <div className="suggestion-body">
                      <p className="suggestion-summary">{suggestion.issue_summary}</p>
                      {suggestion.recommended_steps.length > 0 ? (
                        <ol className="resolution-steps">
                          {suggestion.recommended_steps.map((step, index) => (
                            <li key={`${step.document_id}-${index}`}>
                              <span>{index + 1}</span>
                              <div>
                                {step.text}
                                <small>
                                  Source: {step.document_id} · {step.source_reference}
                                </small>
                              </div>
                            </li>
                          ))}
                        </ol>
                      ) : (
                        <p className="insufficient-note">
                          {suggestion.manual_review_reason}
                        </p>
                      )}

                      {suggestion.supporting_sources.length > 0 && (
                        <div className="source-list">
                          <span className="mini-label">SUPPORTING SOURCES</span>
                          {suggestion.supporting_sources.map((source) => (
                            <div className="source-chip" key={source.document_id}>
                              <FileText size={14} />
                              <span>{source.title}</span>
                              <small>
                                {source.retrieval_score.toFixed(3)} cosine similarity
                              </small>
                            </div>
                          ))}
                        </div>
                      )}
                      <p className="confidence-warning">
                        {suggestion.confidence_warning}
                      </p>
                      {suggestion.manual_review_required && (
                        <p className="review-warning">
                          <ShieldAlert size={15} />
                          {suggestion.manual_review_reason}
                        </p>
                      )}

                      {suggestion.approved_resolution && (
                        <div className="approved-resolution">
                          <span><CheckCircle2 size={15} /> Approved resolution</span>
                          <p>{suggestion.approved_resolution}</p>
                          {suggestion.reviewer && (
                            <small>
                              Reviewed by {suggestion.reviewer} · {formatDate(suggestion.reviewed_at, true)}
                            </small>
                          )}
                        </div>
                      )}

                      {suggestion.status === 'pending' && (
                        <div className="review-controls">
                          {editingId === suggestion.id ? (
                            <div className="edit-resolution">
                              <label className="field-label" htmlFor={`edit-${suggestion.id}`}>
                                Edit resolution text
                              </label>
                              <textarea
                                id={`edit-${suggestion.id}`}
                                className="form-input form-textarea"
                                rows={4}
                                maxLength={10000}
                                value={editedResolution}
                                onChange={(event) => setEditedResolution(event.target.value)}
                                placeholder="Write the resolution you approve..."
                              />
                              <div className="review-button-row">
                                <Button
                                  onClick={() => void reviewSuggestion(suggestion, 'edited')}
                                  disabled={working || !editedResolution.trim()}
                                >
                                  <Check size={15} /> Save edited resolution
                                </Button>
                                <Button
                                  variant="ghost"
                                  onClick={() => {
                                    setEditingId(null)
                                    setEditedResolution('')
                                  }}
                                >
                                  Cancel
                                </Button>
                              </div>
                            </div>
                          ) : (
                            <>
                              <span className="reviewer-note">Reviewing as demo-reviewer-1</span>
                              <div className="review-button-row">
                                <Button
                                  onClick={() => void reviewSuggestion(suggestion, 'accepted')}
                                  disabled={working || suggestion.evidence_state !== 'suggested'}
                                  title={
                                    suggestion.evidence_state !== 'suggested'
                                      ? 'Suggestions without reliable evidence cannot be accepted'
                                      : undefined
                                  }
                                >
                                  <Check size={15} /> Accept
                                </Button>
                                <Button
                                  variant="secondary"
                                  onClick={() => {
                                    setEditingId(suggestion.id)
                                    setEditedResolution(suggestion.suggested_resolution)
                                  }}
                                  disabled={working}
                                >
                                  <Pencil size={15} /> Edit
                                </Button>
                                <Button
                                  variant="danger"
                                  onClick={() => void reviewSuggestion(suggestion, 'rejected')}
                                  disabled={working}
                                >
                                  <X size={15} /> Reject
                                </Button>
                              </div>
                            </>
                          )}
                        </div>
                      )}
                    </div>
                  </article>
                ))}
              </div>
            )}
          </Card>

          <Card className="history-card">
            <SectionTitle
              title="Ticket history"
              subtitle="An audit trail of ticket and review activity"
            />
            {history.length === 0 ? (
              <EmptyState title="No history recorded" description="Ticket events will appear here." />
            ) : (
              <div className="timeline">
                {history.map((event) => (
                  <div className="timeline-item" key={event.id}>
                    <span className="timeline-mark">
                      {event.event_type.startsWith('suggestion_') ? (
                        <Sparkles size={14} />
                      ) : (
                        <Clock3 size={14} />
                      )}
                    </span>
                    <div className="timeline-content">
                      <div className="timeline-heading">
                        <strong>{eventLabels[event.event_type] ?? event.event_type.replaceAll('_', ' ')}</strong>
                        <time>{formatDate(event.timestamp, true)}</time>
                      </div>
                      <p>Actor: {event.actor}</p>
                      {(event.previous_value || event.new_value) && (
                        <small className="timeline-values">
                          {readableValue(event.previous_value)}
                          {event.previous_value && event.new_value ? ' → ' : ''}
                          {readableValue(event.new_value)}
                        </small>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>

        <aside className="ticket-detail-side">
          <Card className="status-control-card">
            <SectionTitle title="Update status" />
            {nextStatuses[ticket.status].length > 0 ? (
              <>
                <label className="field-label" htmlFor="next-status">Move ticket to</label>
                <select
                  id="next-status"
                  className="form-input form-select"
                  value={nextStatus}
                  onChange={(event) => setNextStatus(event.target.value as TicketStatus | '')}
                >
                  <option value="">Select a status</option>
                  {nextStatuses[ticket.status].map((status) => (
                    <option key={status} value={status}>{status.replaceAll('_', ' ')}</option>
                  ))}
                </select>
                <Button
                  className="w-full mt-3"
                  onClick={() => void changeStatus()}
                  disabled={working || !nextStatus}
                >
                  {working ? <LoaderCircle className="animate-spin" size={15} /> : <Check size={15} />}
                  Update status
                </Button>
              </>
            ) : (
              <p className="field-hint">
                {ticket.status === 'resolved'
                  ? 'Resolved tickets are closed to further status changes.'
                  : 'This ticket is already escalated to a human team.'}
              </p>
            )}
            <p className="field-hint mt-3">{resolutionHint}</p>
          </Card>

          <Card className="escalation-card">
            <SectionTitle
              title="Escalate to a human"
              subtitle="Assign the ticket to a support team."
              action={<span className="escalation-icon"><ArrowUpRight size={16} /></span>}
            />
            {canEscalate ? (
              <>
                <label className="field-label" htmlFor="escalation-team">Support team</label>
                <select
                  id="escalation-team"
                  className="form-input form-select"
                  value={escalationTeam}
                  onChange={(event) => setEscalationTeam(event.target.value as HumanSupportTeam)}
                >
                  {teams.map((team) => <option key={team}>{team}</option>)}
                </select>
                <label className="field-label mt-4" htmlFor="escalation-reason">
                  Reason <span className="optional-label">Optional</span>
                </label>
                <textarea
                  id="escalation-reason"
                  className="form-input form-textarea"
                  rows={3}
                  maxLength={1000}
                  value={escalationReason}
                  onChange={(event) => setEscalationReason(event.target.value)}
                  placeholder="Add context for the receiving team"
                />
                <Button
                  variant="secondary"
                  className="w-full mt-3"
                  onClick={() => void escalateTicket()}
                  disabled={working}
                >
                  <ArrowUpRight size={15} /> Escalate ticket
                </Button>
                <p className="demo-action-note">Recorded as demo-user · not authentication</p>
              </>
            ) : (
              <p className="field-hint">
                {ticket.status === 'escalated'
                  ? `Assigned to ${ticket.assigned_team}.`
                  : 'Resolved tickets cannot be escalated.'}
              </p>
            )}
          </Card>

          <Card className="ticket-meta-card">
            <SectionTitle title="Ticket info" />
            <div className="meta-row">
              <span>Ticket number</span>
              <strong>{ticket.ticket_number}</strong>
            </div>
            <div className="meta-row">
              <span>Created</span>
              <strong>{formatDate(ticket.created_at, true)}</strong>
            </div>
            <div className="meta-row">
              <span>Updated</span>
              <strong>{formatDate(ticket.updated_at, true)}</strong>
            </div>
            <Link to="/knowledge" className="meta-link">
              Browse knowledge base <ArrowUpRight size={14} />
            </Link>
          </Card>
        </aside>
      </div>
    </div>
  )
}
