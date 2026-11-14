import type { ButtonHTMLAttributes, ReactNode } from 'react'
import {
  AlertCircle,
  ArrowDownRight,
  ArrowUpRight,
  CheckCircle2,
  Clock3,
  LoaderCircle,
  SearchX,
} from 'lucide-react'

import type { TicketPriority, TicketStatus } from './api'

export function Card({
  children,
  className = '',
}: {
  children: ReactNode
  className?: string
}) {
  return <section className={`surface-card ${className}`}>{children}</section>
}

export function Button({
  children,
  variant = 'primary',
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
}) {
  return (
    <button className={`button button-${variant} ${className}`} {...props}>
      {children}
    </button>
  )
}

export function PageHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <div className="page-header">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1 className="page-title">{title}</h1>
        {description && <p className="page-description">{description}</p>}
      </div>
      {action}
    </div>
  )
}

export function StatusPill({ status }: { status: TicketStatus | string }) {
  return (
    <span className={`status-pill status-${status}`}>
      <span className="status-dot" />
      {status.replaceAll('_', ' ')}
    </span>
  )
}

export function PriorityPill({ priority }: { priority: TicketPriority | string }) {
  return <span className={`priority-pill priority-${priority}`}>{priority}</span>
}

export function LoadingState({ label = 'Loading data' }: { label?: string }) {
  return (
    <div className="state-box" role="status">
      <LoaderCircle className="animate-spin text-brand-600" size={22} />
      <span>{label}…</span>
    </div>
  )
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string
  onRetry?: () => void
}) {
  return (
    <div className="error-box" role="alert">
      <AlertCircle size={19} />
      <div className="min-w-0 flex-1">
        <p className="font-semibold">We couldn’t load this data</p>
        <p className="mt-1 break-words text-sm opacity-85">{message}</p>
      </div>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  )
}

export function EmptyState({
  title,
  description,
  icon = 'search',
  action,
}: {
  title: string
  description: string
  icon?: 'search' | 'clock' | 'check'
  action?: ReactNode
}) {
  const Icon =
    icon === 'clock' ? Clock3 : icon === 'check' ? CheckCircle2 : SearchX
  return (
    <div className="empty-state">
      <span className="empty-icon">
        <Icon size={22} />
      </span>
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </div>
  )
}

export function MetricCard({
  label,
  value,
  note,
  icon: Icon,
  tone = 'blue',
  change,
}: {
  label: string
  value: string | number
  note?: string
  icon: typeof Clock3
  tone?: 'blue' | 'violet' | 'amber' | 'green'
  change?: 'up' | 'down'
}) {
  const ChangeIcon = change === 'up' ? ArrowUpRight : ArrowDownRight
  return (
    <Card className="metric-card">
      <div className="metric-top">
        <span className={`metric-icon metric-${tone}`}>
          <Icon size={19} strokeWidth={2} />
        </span>
        {change && (
          <span className="metric-change">
            <ChangeIcon size={14} /> live
          </span>
        )}
      </div>
      <p className="metric-label">{label}</p>
      <p className="metric-value">{value}</p>
      {note && <p className="metric-note">{note}</p>}
    </Card>
  )
}

export function SectionTitle({
  title,
  subtitle,
  action,
}: {
  title: string
  subtitle?: string
  action?: ReactNode
}) {
  return (
    <div className="section-title">
      <div>
        <h2>{title}</h2>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {action}
    </div>
  )
}

export function ErrorInline({ message }: { message: string }) {
  return (
    <p className="inline-error" role="alert">
      <AlertCircle size={16} />
      {message}
    </p>
  )
}
