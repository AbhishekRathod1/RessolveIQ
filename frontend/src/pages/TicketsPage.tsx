import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronLeft, ChevronRight, Plus, Search, SlidersHorizontal, X } from 'lucide-react'

import { api, type Ticket as TicketType, type TicketListResponse } from '../api'
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  PriorityPill,
  StatusPill,
} from '../components'
import { formatCategory, formatDate } from '../utils'

const pageSize = 10
const categories = [
  ['hardware', 'Hardware'],
  ['software', 'Software'],
  ['network', 'Network'],
  ['access', 'Account & Access'],
  ['security', 'Security'],
  ['other', 'Other'],
]
const statuses = [
  ['open', 'Open'],
  ['in_progress', 'In progress'],
  ['pending_review', 'Pending review'],
  ['resolved', 'Resolved'],
  ['escalated', 'Escalated'],
]

export function TicketsPage() {
  const [result, setResult] = useState<TicketListResponse | null>(null)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [category, setCategory] = useState('')
  const [priority, setPriority] = useState('')
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const response = await api.listTickets({
        limit: pageSize,
        offset,
        search: search.trim() || undefined,
        status: status || undefined,
        category: category || undefined,
        priority: priority || undefined,
      })
      setResult(response)
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : 'Ticket list failed to load.')
    } finally {
      setLoading(false)
    }
  }, [category, offset, priority, search, status])

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), search ? 250 : 0)
    return () => window.clearTimeout(timer)
  }, [load, search])

  function resetFilters() {
    setSearch('')
    setStatus('')
    setCategory('')
    setPriority('')
    setOffset(0)
  }

  const hasFilters = Boolean(search || status || category || priority)
  const pageNumber = Math.floor(offset / pageSize) + 1
  const totalPages = result ? Math.max(1, Math.ceil(result.total / pageSize)) : 1

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="SUPPORT OPERATIONS"
        title="Tickets"
        description="Track, prioritize, and move support requests forward."
        action={
          <Link to="/tickets/new" className="button button-primary">
            <Plus size={17} /> New ticket
          </Link>
        }
      />

      <Card className="tickets-card">
        <div className="filters-toolbar">
          <label className="search-field">
            <Search size={17} />
            <input
              type="search"
              value={search}
              onChange={(event) => {
                setSearch(event.target.value)
                setOffset(0)
              }}
              placeholder="Search tickets..."
              aria-label="Search tickets"
            />
            {search && (
              <button
                type="button"
                className="search-clear"
                aria-label="Clear search"
                onClick={() => setSearch('')}
              >
                <X size={15} />
              </button>
            )}
          </label>
          <div className="filter-controls">
            <span className="filter-label"><SlidersHorizontal size={15} /> Filter by</span>
            <select
              value={status}
              onChange={(event) => {
                setStatus(event.target.value)
                setOffset(0)
              }}
              aria-label="Filter by status"
            >
              <option value="">All statuses</option>
              {statuses.map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
            <select
              value={category}
              onChange={(event) => {
                setCategory(event.target.value)
                setOffset(0)
              }}
              aria-label="Filter by category"
            >
              <option value="">All categories</option>
              {categories.map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
            <select
              value={priority}
              onChange={(event) => {
                setPriority(event.target.value)
                setOffset(0)
              }}
              aria-label="Filter by priority"
            >
              <option value="">All priorities</option>
              <option value="urgent">Urgent</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
            {hasFilters && (
              <button type="button" className="clear-filters" onClick={resetFilters}>
                Clear
              </button>
            )}
          </div>
        </div>

        {loading ? (
          <LoadingState label="Loading tickets" />
        ) : error ? (
          <div className="table-error">
            <ErrorState message={error} onRetry={() => void load()} />
          </div>
        ) : !result || result.items.length === 0 ? (
          <EmptyState
            title={hasFilters ? 'No matching tickets' : 'No tickets yet'}
            description={
              hasFilters
                ? 'Try changing your search or filters.'
                : 'Create a ticket to start tracking support work.'
            }
            action={
              hasFilters ? (
                <Button variant="secondary" className="mt-4" onClick={resetFilters}>
                  Clear filters
                </Button>
              ) : (
                <Link to="/tickets/new" className="button button-primary mt-4">
                  <Plus size={16} /> Create first ticket
                </Link>
              )
            }
          />
        ) : (
          <>
            <div className="table-scroll">
              <table className="data-table tickets-table">
                <thead>
                  <tr>
                    <th>Ticket</th>
                    <th>Category</th>
                    <th>Priority</th>
                    <th>Assigned team</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th aria-label="Open ticket" />
                  </tr>
                </thead>
                <tbody>
                  {result.items.map((ticket: TicketType) => (
                    <tr key={ticket.id}>
                      <td>
                        <Link className="ticket-cell-link" to={`/tickets/${ticket.id}`}>
                          <span className="ticket-number">{ticket.ticket_number}</span>
                          <span className="ticket-title">{ticket.title}</span>
                        </Link>
                      </td>
                      <td><span className="category-cell">{formatCategory(ticket.category)}</span></td>
                      <td><PriorityPill priority={ticket.priority} /></td>
                      <td className="team-cell">{ticket.assigned_team}</td>
                      <td><StatusPill status={ticket.status} /></td>
                      <td className="muted-cell">{formatDate(ticket.created_at)}</td>
                      <td>
                        <Link
                          to={`/tickets/${ticket.id}`}
                          className="table-open-link"
                          aria-label={`Open ${ticket.ticket_number}`}
                        >
                          <ChevronRight size={17} />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="table-pagination">
              <span>
                Showing <strong>{offset + 1}</strong>–<strong>{offset + result.items.length}</strong>
                {' '}of <strong>{result.total}</strong> tickets
              </span>
              <div>
                <button
                  type="button"
                  className="pagination-button"
                  onClick={() => setOffset((value) => Math.max(0, value - pageSize))}
                  disabled={offset === 0}
                  aria-label="Previous page"
                >
                  <ChevronLeft size={17} /> Previous
                </button>
                <span className="page-count">Page {pageNumber} of {totalPages}</span>
                <button
                  type="button"
                  className="pagination-button"
                  onClick={() => setOffset((value) => value + pageSize)}
                  disabled={offset + pageSize >= result.total}
                  aria-label="Next page"
                >
                  Next <ChevronRight size={17} />
                </button>
              </div>
            </div>
          </>
        )}
      </Card>
    </div>
  )
}
