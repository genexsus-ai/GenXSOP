import api from './api'
import type { DashboardSummary, DashboardAlert } from '@/types'

type BackendDashboardSummary = {
  demand_plans?: { draft?: number; submitted?: number; approved?: number; total?: number }
  inventory_health?: {
    total_products?: number
    normal?: number
    low?: number
    critical?: number
    excess?: number
    total_value?: number
  }
  kpis?: { forecast_accuracy?: number | null; otif?: number | null }
  sop_cycle?: { id?: number | null; name?: string | null; current_step?: number | null; status?: string | null } | null
}

type BackendDashboardAlerts = {
  inventory_critical?: Array<{ product_id: number; location: string; on_hand: number }>
  inventory_low?: Array<{ product_id: number; location: string; on_hand: number }>
  kpi_alerts?: Array<{ severity: 'critical' | 'warning' | 'info'; message: string; metric?: string; value?: number; target?: number }>
  total_alerts?: number
}

function sopStepLabel(step?: number | null): string | undefined {
  if (!step) return undefined
  const map: Record<number, string> = {
    1: 'Data Gathering',
    2: 'Demand Review',
    3: 'Supply Review',
    4: 'Pre-S&OP',
    5: 'Executive S&OP',
  }
  return map[step] ?? `Step ${step}`
}

function normalizeSummary(raw: BackendDashboardSummary): DashboardSummary {
  const inv = raw.inventory_health ?? {}
  const dp = raw.demand_plans ?? {}
  const kpis = raw.kpis ?? {}
  const cycle = raw.sop_cycle

  return {
    total_products: inv.total_products ?? 0,
    active_demand_plans: dp.total ?? 0,
    active_supply_plans: 0,
    inventory_alerts: (inv.low ?? 0) + (inv.critical ?? 0),
    pending_approvals: dp.submitted ?? 0,
    active_sop_cycles: cycle?.status === 'active' ? 1 : 0,
    total_inventory_value: inv.total_value ?? 0,
    forecast_accuracy: kpis.forecast_accuracy ?? 0,
    forecast_accuracy_change: undefined,
    otif_rate: kpis.otif ?? 0,
    otif_change: undefined,
    low_stock_count: inv.low ?? 0,
    active_sop_cycle: cycle?.name ?? undefined,
    sop_cycle_stage: sopStepLabel(cycle?.current_step),
    demand_plans_count: dp.total ?? 0,
    supply_plans_count: 0,
    open_scenarios_count: 0,
    products_count: inv.total_products ?? 0,
    recent_activity: [],
  }
}

function normalizeAlerts(raw: BackendDashboardAlerts): DashboardAlert[] {
  const now = new Date().toISOString()
  const out: DashboardAlert[] = []

  for (const i of raw.inventory_critical ?? []) {
    out.push({
      id: `inv-critical-${i.product_id}-${i.location}`,
      type: 'critical',
      severity: 'critical',
      title: 'Critical inventory',
      message: `Product #${i.product_id} at ${i.location} has ${i.on_hand} on hand`,
      entity_type: 'inventory',
      entity_id: i.product_id,
      created_at: now,
    })
  }

  for (const i of raw.inventory_low ?? []) {
    out.push({
      id: `inv-low-${i.product_id}-${i.location}`,
      type: 'warning',
      severity: 'warning',
      title: 'Low inventory',
      message: `Product #${i.product_id} at ${i.location} has ${i.on_hand} on hand`,
      entity_type: 'inventory',
      entity_id: i.product_id,
      created_at: now,
    })
  }

  for (const k of raw.kpi_alerts ?? []) {
    out.push({
      id: `kpi-${k.metric ?? k.message}`,
      type: k.severity === 'critical' ? 'critical' : k.severity === 'warning' ? 'warning' : 'info',
      severity: k.severity,
      title: k.metric ? `KPI: ${k.metric}` : 'KPI alert',
      message: k.message,
      entity_type: 'kpi',
      created_at: now,
    })
  }

  return out
}

export const dashboardService = {
  async getSummary(): Promise<DashboardSummary> {
    // Backend response shape differs from the UI's DashboardSummary model.
    // Normalize here so pages can stay simple.
    const res = await api.get<BackendDashboardSummary>('/dashboard/summary')
    return normalizeSummary(res.data)
  },

  async getAlerts(): Promise<DashboardAlert[]> {
    const res = await api.get<BackendDashboardAlerts>('/dashboard/alerts')
    return normalizeAlerts(res.data)
  },

  async getSOPStatus() {
    const res = await api.get('/dashboard/sop-status')
    return res.data
  },

  async getKPIOverview() {
    const res = await api.get('/dashboard/kpi-overview')
    return res.data
  },
}
