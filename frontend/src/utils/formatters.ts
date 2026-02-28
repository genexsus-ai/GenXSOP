import { format, parseISO } from 'date-fns'

function toSafeNumber(value: number | string | null | undefined): number | null {
  if (value == null) return null
  const parsed = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

// ── Number formatters ─────────────────────────────────────────────────────────

export function formatNumber(value: number | string | null | undefined, decimals = 0): string {
  const safe = toSafeNumber(value)
  if (safe == null) return '—'
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(safe)
}

export function formatCurrency(value: number | string | null | undefined, currency = 'USD'): string {
  const safe = toSafeNumber(value)
  if (safe == null) return '—'

  if (safe >= 1_000_000) {
    return `$${(safe / 1_000_000).toFixed(1)}M`
  }
  if (safe >= 1_000) {
    return `$${(safe / 1_000).toFixed(1)}K`
  }
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(safe)
}

export function formatPercent(value: number | string | null | undefined, decimals = 1): string {
  const safe = toSafeNumber(value)
  if (safe == null) return '—'
  return `${safe.toFixed(decimals)}%`
}

export function formatQuantity(value: number | string | null | undefined): string {
  const safe = toSafeNumber(value)
  if (safe == null) return '—'
  if (safe >= 1_000_000) return `${(safe / 1_000_000).toFixed(1)}M`
  if (safe >= 1_000) return `${(safe / 1_000).toFixed(1)}K`
  return formatNumber(safe)
}

// ── Date formatters ───────────────────────────────────────────────────────────

export function formatDate(dateStr: string, fmt = 'MMM d, yyyy'): string {
  try {
    return format(parseISO(dateStr), fmt)
  } catch {
    return dateStr
  }
}

export function formatPeriod(dateStr: string): string {
  try {
    return format(parseISO(dateStr), 'MMM yyyy')
  } catch {
    return dateStr
  }
}

export function formatDateTime(dateStr: string): string {
  try {
    return format(parseISO(dateStr), 'MMM d, yyyy HH:mm')
  } catch {
    return dateStr
  }
}

// ── Status formatters ─────────────────────────────────────────────────────────

export function formatStatus(status: string): string {
  return status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

export function getStatusColor(status: string): string {
  const map: Record<string, string> = {
    draft: 'badge-draft',
    submitted: 'badge-submitted',
    approved: 'badge-approved',
    rejected: 'badge-rejected',
    locked: 'badge-locked',
    active: 'badge-active',
    completed: 'badge-completed',
    cancelled: 'badge-cancelled',
    normal: 'badge-normal',
    low: 'badge-low',
    critical: 'badge-critical',
    excess: 'badge-excess',
    pending: 'badge-draft',
    in_progress: 'badge-submitted',
  }
  return map[status] ?? 'badge-draft'
}

// ── Trend helpers ─────────────────────────────────────────────────────────────

export function getTrendIcon(trend?: string): string {
  if (trend === 'improving') return '↑'
  if (trend === 'declining') return '↓'
  return '→'
}

export function getTrendColor(trend?: string): string {
  if (trend === 'improving') return 'text-emerald-600'
  if (trend === 'declining') return 'text-red-500'
  return 'text-gray-500'
}

export function getChangeColor(change: number): string {
  if (change > 0) return 'text-emerald-600'
  if (change < 0) return 'text-red-500'
  return 'text-gray-500'
}

// ── Role helpers ──────────────────────────────────────────────────────────────

export function formatRole(role: string): string {
  const map: Record<string, string> = {
    admin: 'Administrator',
    executive: 'Executive',
    demand_planner: 'Demand Planner',
    supply_planner: 'Supply Planner',
    inventory_manager: 'Inventory Manager',
    finance_analyst: 'Finance Analyst',
    sop_coordinator: 'S&OP Coordinator',
    viewer: 'Viewer',
  }
  return map[role] ?? role
}
