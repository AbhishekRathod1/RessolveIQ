import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Check, LoaderCircle, Sparkles } from 'lucide-react'

import { api, type Analysis, type TicketPriority } from '../api'
import {
  Button,
  Card,
  ErrorInline,
  PageHeader,
  PriorityPill,
} from '../components'

const categoryOptions = [
  { value: 'hardware', label: 'Hardware' },
  { value: 'software', label: 'Software' },
  { value: 'network', label: 'Network' },
  { value: 'access', label: 'Account & Access' },
  { value: 'security', label: 'Security' },
  { value: 'other', label: 'Other' },
]
const predictedCategories: Record<Analysis['predicted_category'], string> = {
  Hardware: 'hardware',
  Software: 'software',
  Network: 'network',
  'Account & Access': 'access',
  Security: 'security',
  Other: 'other',
}

export function NewTicketPage() {
  const navigate = useNavigate()
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [requesterName, setRequesterName] = useState('')
  const [requesterEmail, setRequesterEmail] = useState('')
  const [businessImpact, setBusinessImpact] = useState('')
  const [category, setCategory] = useState('other')
  const [priority, setPriority] = useState<TicketPriority>('medium')
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [analysisError, setAnalysisError] = useState('')
  const [analyzing, setAnalyzing] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState('')

  async function runAnalysis() {
    setAnalyzing(true)
    setAnalysisError('')
    setAnalysis(null)
    try {
      const result = await api.analyzeTicket(
        title,
        description,
        businessImpact || undefined,
      )
      setAnalysis(result)
    } catch (issue) {
      setAnalysisError(
        issue instanceof Error ? issue.message : 'AI analysis is unavailable.',
      )
    } finally {
      setAnalyzing(false)
    }
  }

  function applyRecommendation() {
    if (!analysis) return
    setCategory(predictedCategories[analysis.predicted_category])
    setPriority(
      analysis.recommended_priority === 'critical'
        ? 'urgent'
        : analysis.recommended_priority,
    )
  }

  async function submitTicket(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    setSubmitError('')
    try {
      const ticket = await api.createTicket({
        title: title.trim(),
        description: description.trim(),
        category,
        priority,
        requester_name: requesterName.trim(),
        requester_email: requesterEmail.trim(),
      })
      navigate(`/tickets/${ticket.id}`)
    } catch (issue) {
      setSubmitError(
        issue instanceof Error ? issue.message : 'The ticket could not be created.',
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="SUPPORT OPERATIONS / NEW"
        title="Create a ticket"
        description="Capture the issue details. AI recommendations are optional and never applied without your action."
        action={
          <button type="button" className="button button-ghost" onClick={() => navigate(-1)}>
            <ArrowLeft size={16} /> Back
          </button>
        }
      />

      <form className="new-ticket-layout" onSubmit={(event) => void submitTicket(event)}>
        <div className="new-ticket-main">
          <Card className="form-card">
            <div className="form-section-heading">
              <span className="form-step">01</span>
              <div>
                <h2>Issue details</h2>
                <p>Describe what happened and how it affects work.</p>
              </div>
            </div>
            <label className="field-label" htmlFor="ticket-title">Ticket title <span>*</span></label>
            <input
              id="ticket-title"
              className="form-input"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="e.g. Cannot connect to the company VPN"
              maxLength={200}
              required
            />
            <div className="field-meta">
              <span>Use a short, descriptive summary</span>
              <span>{title.length}/200</span>
            </div>

            <label className="field-label mt-5" htmlFor="ticket-description">
              Description <span>*</span>
            </label>
            <textarea
              id="ticket-description"
              className="form-input form-textarea"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Include what you were trying to do, what happened, and any error messages."
              maxLength={10000}
              rows={6}
              required
            />
            <div className="field-meta">
              <span>Do not include passwords or sensitive credentials</span>
              <span>{description.length}/10,000</span>
            </div>

            <label className="field-label mt-5" htmlFor="business-impact">
              Business impact <span className="optional-label">Optional</span>
            </label>
            <textarea
              id="business-impact"
              className="form-input form-textarea"
              value={businessImpact}
              onChange={(event) => setBusinessImpact(event.target.value)}
              placeholder="Who is affected? Is a critical business function blocked?"
              maxLength={1000}
              rows={3}
            />
            <p className="field-hint">Used only to inform the AI priority recommendation.</p>
          </Card>

          <Card className="form-card">
            <div className="form-section-heading">
              <span className="form-step">02</span>
              <div>
                <h2>Requester</h2>
                <p>Who should support contact about this request?</p>
              </div>
            </div>
            <div className="form-two-col">
              <div>
                <label className="field-label" htmlFor="requester-name">Full name <span>*</span></label>
                <input
                  id="requester-name"
                  className="form-input"
                  value={requesterName}
                  onChange={(event) => setRequesterName(event.target.value)}
                  placeholder="Alex Example"
                  maxLength={120}
                  required
                />
              </div>
              <div>
                <label className="field-label" htmlFor="requester-email">Work email <span>*</span></label>
                <input
                  id="requester-email"
                  className="form-input"
                  type="email"
                  value={requesterEmail}
                  onChange={(event) => setRequesterEmail(event.target.value)}
                  placeholder="alex@example.com"
                  maxLength={254}
                  required
                />
              </div>
            </div>
          </Card>
        </div>

        <aside className="new-ticket-side">
          <Card className="classification-card">
            <div className="form-section-heading">
              <span className="ai-orb"><Sparkles size={17} /></span>
              <div>
                <h2>Classification</h2>
                <p>Choose manually or ask AI for a suggestion.</p>
              </div>
            </div>
            <label className="field-label" htmlFor="ticket-category">Category</label>
            <select
              id="ticket-category"
              className="form-input form-select"
              value={category}
              onChange={(event) => setCategory(event.target.value)}
            >
              {categoryOptions.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>

            <label className="field-label mt-4" htmlFor="ticket-priority">Priority</label>
            <select
              id="ticket-priority"
              className="form-input form-select"
              value={priority}
              onChange={(event) => setPriority(event.target.value as TicketPriority)}
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="urgent">Urgent</option>
            </select>

            <Button
              type="button"
              variant="secondary"
              className="w-full mt-5"
              onClick={() => void runAnalysis()}
              disabled={analyzing || !title.trim() || !description.trim()}
            >
              {analyzing ? (
                <><LoaderCircle className="animate-spin" size={16} /> Analyzing…</>
              ) : (
                <><Sparkles size={16} /> Analyze with AI</>
              )}
            </Button>

            {analysisError && <ErrorInline message={analysisError} />}
            {analysis && (
              <div className="analysis-result">
                <div className="analysis-result-top">
                  <div>
                    <span className="mini-label">SUGGESTED CATEGORY</span>
                    <strong>{analysis.predicted_category}</strong>
                  </div>
                  {analysis.needs_manual_review && (
                    <span className="review-needed">Review recommended</span>
                  )}
                </div>
                <div className="analysis-meta-row">
                  <span>Model confidence</span>
                  <strong>{(analysis.category_confidence * 100).toFixed(1)}%</strong>
                </div>
                <div className="analysis-meta-row">
                  <span>Rule-based priority</span>
                  <PriorityPill
                    priority={
                      analysis.recommended_priority === 'critical'
                        ? 'urgent'
                        : analysis.recommended_priority
                    }
                  />
                </div>
                <div className="analysis-meta-row">
                  <span>Recommended team</span>
                  <strong>{analysis.recommended_team}</strong>
                </div>
                <p className="analysis-explanation">{analysis.explanation}</p>
                <Button
                  type="button"
                  variant="ghost"
                  className="analysis-apply"
                  onClick={applyRecommendation}
                >
                  <Check size={15} /> Apply recommendation
                </Button>
                <p className="field-hint mt-2">
                  Applying is optional. Your chosen values remain editable.
                </p>
              </div>
            )}
          </Card>

          <div className="form-submit-panel">
            {submitError && <ErrorInline message={submitError} />}
            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? (
                <><LoaderCircle className="animate-spin" size={16} /> Creating…</>
              ) : (
                <>Create ticket <ArrowRight size={16} /></>
              )}
            </Button>
            <p>Ticket ID and timestamps are assigned by ResolveIQ.</p>
          </div>
        </aside>
      </form>
    </div>
  )
}
