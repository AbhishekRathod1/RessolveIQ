import { useCallback, useEffect, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  Activity,
  CheckCircle2,
  Clock3,
  Sparkles,
  Ticket,
  Users,
} from 'lucide-react'

import { api, type AnalyticsSummary } from '../api'
import {
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  MetricCard,
  PageHeader,
  SectionTitle,
} from '../components'
import { formatCategory, formatDuration } from '../utils'

const priorityColors: Record<string, string> = {
  low: '#10b981',
  medium: '#0ea5e9',
  high: '#f59e0b',
  urgent: '#ef4444',
}
const statusColors: Record<string, string> = {
  open: '#6366f1',
  in_progress: '#0ea5e9',
  pending_review: '#f59e0b',
  resolved: '#10b981',
  escalated: '#ef4444',
}

function getAnalytics() {
  return api.analytics()
}

function ChartTooltip({
  active,
  payload,
}: {
  active?: boolean
  payload?: Array<{ value: number; payload?: { label?: string; name?: string } }>
}) {
  if (!active || !payload?.length) return null
  const point = payload[0]
  return (
    <div className="chart-tooltip">
      <strong>{point.payload?.label ?? point.payload?.name}</strong>
      <span>{point.value} tickets</span>
    </div>
  )
}

export function AnalyticsPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setSummary(await getAnalytics())
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : 'Analytics failed to load.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    let active = true
    void getAnalytics().then(
      (data) => {
        if (active) setSummary(data)
      },
      (issue: unknown) => {
        if (active) {
          setError(
            issue instanceof Error ? issue.message : 'Analytics failed to load.',
          )
        }
      },
    ).finally(() => {
      if (active) setLoading(false)
    })
    return () => {
      active = false
    }
  }, [])

  if (loading) return <LoadingState label="Loading analytics" />
  if (error || !summary) {
    return (
      <ErrorState
        message={error || 'Analytics are not available right now.'}
        onRetry={() => void load()}
      />
    )
  }

  const statusData = Object.entries(summary.tickets_by_status).map(([name, value]) => ({
    name,
    label: name.replaceAll('_', ' '),
    value,
  }))
  const categoryData = Object.entries(summary.tickets_by_category).map(([name, value]) => ({
    name,
    label: formatCategory(name),
    value,
  }))
  const priorityData = ['low', 'medium', 'high', 'urgent'].map((name) => ({
    name,
    label: name,
    value: summary.tickets_by_priority[name as keyof typeof summary.tickets_by_priority] ?? 0,
  }))

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="REPORTING"
        title="Analytics"
        description="Operational metrics from the current ResolveIQ ticket database."
        action={
          <span className="data-source-label"><Activity size={14} /> Live database metrics</span>
        }
      />

      <div className="metric-grid analytics-metric-grid">
        <MetricCard
          label="Total tickets"
          value={summary.total_tickets.toLocaleString()}
          note="All time"
          icon={Ticket}
          tone="blue"
        />
        <MetricCard
          label="Open tickets"
          value={summary.open_tickets.toLocaleString()}
          note="Current open status"
          icon={Activity}
          tone="amber"
        />
        <MetricCard
          label="Avg. resolution"
          value={formatDuration(summary.average_resolution_time_seconds)}
          note={`Based on ${summary.average_resolution_time_ticket_count} resolved tickets`}
          icon={Clock3}
          tone="violet"
        />
        <MetricCard
          label="Suggestion acceptance"
          value={
            summary.ai_suggestion_acceptance_rate === null
              ? 'N/A'
              : `${(summary.ai_suggestion_acceptance_rate * 100).toFixed(1)}%`
          }
          note={`From ${summary.ai_suggestion_reviewed_count} reviewed suggestions`}
          icon={Sparkles}
          tone="green"
        />
      </div>

      <div className="analytics-chart-grid">
        <Card className="chart-card analytics-chart-card">
          <SectionTitle
            title="Ticket volume by status"
            subtitle="Current ticket counts across lifecycle states"
          />
          {summary.total_tickets === 0 ? (
            <EmptyState title="No ticket volume yet" description="Status totals will appear after tickets are created." />
          ) : (
            <div className="chart-area chart-bar">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={statusData} margin={{ top: 8, right: 12, left: -20, bottom: 4 }}>
                  <CartesianGrid stroke="#eef0f5" vertical={false} />
                  <XAxis
                    dataKey="label"
                    tickLine={false}
                    axisLine={false}
                    tick={{ fill: '#788195', fontSize: 11 }}
                  />
                  <YAxis
                    allowDecimals={false}
                    tickLine={false}
                    axisLine={false}
                    tick={{ fill: '#9aa1b1', fontSize: 11 }}
                  />
                  <Tooltip content={<ChartTooltip />} cursor={{ fill: '#f6f7fb' }} />
                  <Bar dataKey="value" name="Tickets" radius={[6, 6, 0, 0]} maxBarSize={48}>
                    {statusData.map((item) => (
                      <Cell key={item.name} fill={statusColors[item.name]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        <Card className="chart-card analytics-chart-card">
          <SectionTitle
            title="Category breakdown"
            subtitle="Tickets grouped by recorded category"
          />
          {categoryData.length === 0 ? (
            <EmptyState title="No category data" description="Category counts will appear when tickets are created." />
          ) : (
            <div className="chart-area chart-bar">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={categoryData}
                  layout="vertical"
                  margin={{ top: 8, right: 12, left: 16, bottom: 4 }}
                >
                  <CartesianGrid stroke="#eef0f5" horizontal={false} />
                  <XAxis
                    type="number"
                    allowDecimals={false}
                    tickLine={false}
                    axisLine={false}
                    tick={{ fill: '#9aa1b1', fontSize: 11 }}
                  />
                  <YAxis
                    type="category"
                    dataKey="label"
                    width={104}
                    tickLine={false}
                    axisLine={false}
                    tick={{ fill: '#788195', fontSize: 11 }}
                  />
                  <Tooltip content={<ChartTooltip />} cursor={{ fill: '#f6f7fb' }} />
                  <Bar dataKey="value" name="Tickets" fill="#4f46e5" radius={[0, 6, 6, 0]} maxBarSize={26} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        <Card className="chart-card analytics-chart-card">
          <SectionTitle
            title="Priority distribution"
            subtitle="Tickets by selected priority"
          />
          {summary.total_tickets === 0 ? (
            <EmptyState title="No priority data" description="Priority counts will appear when tickets are created." />
          ) : (
            <div className="chart-area chart-bar">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={priorityData} margin={{ top: 8, right: 12, left: -20, bottom: 4 }}>
                  <CartesianGrid stroke="#eef0f5" vertical={false} />
                  <XAxis
                    dataKey="label"
                    tickLine={false}
                    axisLine={false}
                    tick={{ fill: '#788195', fontSize: 11 }}
                  />
                  <YAxis
                    allowDecimals={false}
                    tickLine={false}
                    axisLine={false}
                    tick={{ fill: '#9aa1b1', fontSize: 11 }}
                  />
                  <Tooltip content={<ChartTooltip />} cursor={{ fill: '#f6f7fb' }} />
                  <Bar dataKey="value" name="Tickets" radius={[6, 6, 0, 0]} maxBarSize={48}>
                    {priorityData.map((item) => (
                      <Cell key={item.name} fill={priorityColors[item.name]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        <Card className="chart-card analytics-review-card">
          <SectionTitle
            title="AI suggestion reviews"
            subtitle="Human decisions recorded in the workflow"
            action={<span className="ai-small-tag"><Sparkles size={13} /> DEMO AI</span>}
          />
          <div className="review-rate-panel">
            <div className="review-rate-icon"><CheckCircle2 size={20} /></div>
            <div>
              <span>Accepted or edited</span>
              <strong>
                {summary.ai_suggestion_acceptance_rate === null
                  ? 'N/A'
                  : `${(summary.ai_suggestion_acceptance_rate * 100).toFixed(1)}%`}
              </strong>
            </div>
          </div>
          <div className="review-count-list">
            <div><span className="review-count-dot accepted-dot" /> Accepted <strong>{summary.ai_suggestion_accepted_count}</strong></div>
            <div><span className="review-count-dot edited-dot" /> Edited <strong>{summary.ai_suggestion_edited_count}</strong></div>
            <div><span className="review-count-dot rejected-dot" /> Rejected <strong>{summary.ai_suggestion_rejected_count}</strong></div>
            <div><span className="review-count-dot total-dot" /> Reviewed total <strong>{summary.ai_suggestion_reviewed_count}</strong></div>
          </div>
          <p className="chart-footnote">
            Denominator: accepted + edited + rejected. Pending suggestions are excluded.
          </p>
        </Card>
      </div>

      <div className="analytics-note">
        <Users size={16} />
        <p>
          Resolution time averages resolved tickets with valid timestamps ({summary.average_resolution_time_ticket_count} included).
          Metrics are operational counts from this demo database, not predictive model performance.
        </p>
      </div>
    </div>
  )
}
