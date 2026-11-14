import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowUpRight,
  CheckCircle2,
  CircleAlert,
  Clock3,
  Layers3,
  Plus,
  Sparkles,
  Ticket,
} from 'lucide-react'
import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'

import { api, type AnalyticsSummary, type Ticket as TicketType } from '../api'
import {
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  MetricCard,
  PageHeader,
  PriorityPill,
  SectionTitle,
  StatusPill,
} from '../components'
import { formatCategory, formatDate } from '../utils'

const categoryColors = ['#4f46e5', '#0ea5e9', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']
const statusColors: Record<string, string> = {
  open: '#6366f1',
  in_progress: '#0ea5e9',
  pending_review: '#f59e0b',
  resolved: '#10b981',
  escalated: '#ef4444',
}

function getDashboardData() {
  return Promise.all([
    api.analytics(),
    api.listTickets({ limit: 6, offset: 0 }),
  ] as const)
}

export function DashboardPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null)
  const [recent, setRecent] = useState<TicketType[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [analytics, tickets] = await getDashboardData()
      setSummary(analytics)
      setRecent(tickets.items)
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : 'Dashboard data failed to load.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    let active = true
    void getDashboardData().then(
      ([analytics, tickets]) => {
        if (active) {
          setSummary(analytics)
          setRecent(tickets.items)
        }
      },
      (issue: unknown) => {
        if (active) {
          setError(
            issue instanceof Error
              ? issue.message
              : 'Dashboard data failed to load.',
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

  if (loading) return <LoadingState label="Loading your dashboard" />
  if (error || !summary) {
    return (
      <ErrorState
        message={error || 'Analytics are not available right now.'}
        onRetry={() => void load()}
      />
    )
  }

  const categoryData = Object.entries(summary.tickets_by_category).map(
    ([name, value]) => ({ name: formatCategory(name), value }),
  )
  const statusData = Object.entries(summary.tickets_by_status)
    .filter(([, value]) => value > 0)
    .map(([name, value]) => ({ name: name.replaceAll('_', ' '), value, key: name }))
  const acceptance = summary.ai_suggestion_acceptance_rate

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="OVERVIEW"
        title="Good day, team"
        description="A clear view of your support queue and AI-assisted workflow."
        action={
          <Link to="/tickets/new" className="button button-primary">
            <Plus size={17} /> Create ticket
          </Link>
        }
      />

      <div className="metric-grid">
        <MetricCard
          label="Total tickets"
          value={summary.total_tickets.toLocaleString()}
          note="All tickets in workspace"
          icon={Layers3}
          tone="blue"
        />
        <MetricCard
          label="Open tickets"
          value={summary.open_tickets.toLocaleString()}
          note="Awaiting support"
          icon={CircleAlert}
          tone="amber"
        />
        <MetricCard
          label="Resolved"
          value={summary.resolved_tickets.toLocaleString()}
          note="Successfully closed"
          icon={CheckCircle2}
          tone="green"
        />
        <MetricCard
          label="Escalated"
          value={(summary.tickets_by_status.escalated ?? 0).toLocaleString()}
          note="With a human team"
          icon={ArrowUpRight}
          tone="violet"
        />
      </div>

      <div className="dashboard-chart-grid">
        <Card className="chart-card">
          <SectionTitle
            title="Tickets by category"
            subtitle="Live distribution across the current queue"
            action={<span className="chart-tag">All tickets</span>}
          />
          {categoryData.length === 0 ? (
            <EmptyState
              title="No ticket categories yet"
              description="Category distribution will appear once tickets are created."
              icon="check"
            />
          ) : (
            <div className="chart-area chart-donut">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={categoryData}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={66}
                    outerRadius={94}
                    paddingAngle={3}
                    stroke="none"
                  >
                    {categoryData.map((item, index) => (
                      <Cell
                        key={item.name}
                        fill={categoryColors[index % categoryColors.length]}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value) => [value, 'Tickets']}
                    contentStyle={{ borderRadius: 12, borderColor: '#e8eaf0' }}
                  />
                  <Legend
                    verticalAlign="bottom"
                    iconType="circle"
                    iconSize={8}
                    wrapperStyle={{ fontSize: 12, paddingTop: 16 }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="donut-center">
                <strong>{summary.total_tickets}</strong>
                <span>tickets</span>
              </div>
            </div>
          )}
        </Card>

        <Card className="chart-card">
          <SectionTitle
            title="Status distribution"
            subtitle="Current ticket lifecycle"
            action={<span className="chart-tag">Live</span>}
          />
          {statusData.length === 0 ? (
            <EmptyState
              title="Nothing in the queue"
              description="Create a ticket to start tracking support work."
              icon="check"
            />
          ) : (
            <div className="status-chart-list">
              {statusData.map((item) => {
                const total = Math.max(summary.total_tickets, 1)
                return (
                  <div className="status-chart-row" key={item.key}>
                    <div className="status-chart-label">
                      <span
                        className="chart-dot"
                        style={{ backgroundColor: statusColors[item.key] }}
                      />
                      <span className="capitalize">{item.name}</span>
                      <strong>{item.value}</strong>
                    </div>
                    <div className="progress-track">
                      <span
                        style={{
                          width: `${(item.value / total) * 100}%`,
                          backgroundColor: statusColors[item.key],
                        }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          )}
          <div className="chart-footnote">
            <span>Ticket volume</span>
            <strong>{summary.total_tickets.toLocaleString()}</strong>
          </div>
        </Card>
      </div>

      <div className="dashboard-bottom-grid">
        <Card className="recent-card">
          <SectionTitle
            title="Recent tickets"
            subtitle="Latest activity in your workspace"
            action={
              <Link to="/tickets" className="text-link">
                View all <ArrowUpRight size={14} />
              </Link>
            }
          />
          {recent.length === 0 ? (
            <EmptyState
              title="Your queue is clear"
              description="Create the first support ticket to begin."
              action={
                <Link to="/tickets/new" className="button button-secondary mt-4">
                  <Plus size={15} /> Create ticket
                </Link>
              }
            />
          ) : (
            <div className="table-scroll">
              <table className="data-table recent-table">
                <thead>
                  <tr>
                    <th>Ticket</th>
                    <th>Category</th>
                    <th>Priority</th>
                    <th>Status</th>
                    <th>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {recent.map((ticket) => (
                    <tr key={ticket.id}>
                      <td>
                        <Link className="ticket-cell-link" to={`/tickets/${ticket.id}`}>
                          <span className="ticket-number">{ticket.ticket_number}</span>
                          <span className="ticket-title">{ticket.title}</span>
                        </Link>
                      </td>
                      <td>{ticket.category}</td>
                      <td><PriorityPill priority={ticket.priority} /></td>
                      <td><StatusPill status={ticket.status} /></td>
                      <td className="muted-cell">{formatDate(ticket.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <Card className="acceptance-card">
          <div className="acceptance-visual">
            <span className="acceptance-icon"><Sparkles size={20} /></span>
            <span className="chart-tag">AI WORKFLOW</span>
          </div>
          <p className="acceptance-label">Suggestion acceptance</p>
          <p className="acceptance-value">
            {acceptance === null ? '—' : `${(acceptance * 100).toFixed(0)}%`}
          </p>
          <p className="acceptance-description">
            {acceptance === null
              ? 'No suggestions have been reviewed yet.'
              : 'Accepted or edited suggestions among all reviewed suggestions.'}
          </p>
          <div className="acceptance-divider" />
          <div className="acceptance-foot">
            <span><Ticket size={15} /> Reviewed suggestions</span>
            <strong>{summary.ai_suggestion_reviewed_count}</strong>
          </div>
          <div className="acceptance-foot">
            <span><Clock3 size={15} /> Needs review</span>
            <strong>
              <Link to="/tickets" className="text-link">
                Open queue <ArrowUpRight size={13} />
              </Link>
            </strong>
          </div>
        </Card>
      </div>

      <p className="data-disclaimer">
        <Sparkles size={14} />
        AI recommendations are assistive and based on fictional demo data.
      </p>
    </div>
  )
}
