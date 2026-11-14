export function formatDate(value: string | null, includeTime = false) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat('en', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    ...(includeTime ? { hour: 'numeric', minute: '2-digit' } : {}),
  }).format(date)
}

export function formatDuration(seconds: number | null) {
  if (seconds === null) return 'N/A'
  const hours = seconds / 3600
  if (hours < 1) return `${Math.max(1, Math.round(seconds / 60))} min`
  if (hours < 48) return `${hours.toFixed(1)} hrs`
  return `${(hours / 24).toFixed(1)} days`
}

export function formatCategory(category: string) {
  const knownCategories: Record<string, string> = {
    hardware: 'Hardware',
    software: 'Software',
    network: 'Network',
    access: 'Account & Access',
    'account & access': 'Account & Access',
    security: 'Security',
    other: 'Other',
  }
  return knownCategories[category.toLowerCase()] ?? category
}
