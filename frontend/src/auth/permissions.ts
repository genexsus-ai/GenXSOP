import type { UserRole } from '@/types'

// Centralized, frontend-only RBAC helpers.
// NOTE: Backend RBAC (FastAPI `require_roles`) remains the source of truth.

export type AppModule =
  | 'dashboard'
  | 'demand'
  | 'supply'
  | 'production_scheduling'
  | 'inventory'
  | 'forecasting'
  | 'scenarios'
  | 'sop_cycle'
  | 'kpi'
  | 'products'
  | 'settings'

export type Permission =
  | 'demand.plan.write'
  | 'demand.plan.approve'
  | 'supply.plan.write'
  | 'supply.plan.approve'
  | 'scenario.write'
  | 'scenario.approve'
  | 'forecast.generate'
  | 'forecast.consensus.approve'
  | 'inventory.update'
  | 'kpi.manage'
  | 'products.manage'
  | 'sop.manage'

const ALL_ROLES: UserRole[] = [
  'admin',
  'executive',
  'demand_planner',
  'supply_planner',
  'inventory_manager',
  'finance_analyst',
  'sop_coordinator',
  'viewer',
]

// Module access: determines route access + sidebar visibility.
// Per your requirement, viewer is limited to Dashboard + KPI (+ Settings for account self-management).
const MODULE_ACCESS: Record<AppModule, UserRole[]> = {
  dashboard: ALL_ROLES,
  kpi: ALL_ROLES,
  settings: ALL_ROLES,

  demand: ['admin', 'executive', 'demand_planner', 'supply_planner', 'sop_coordinator'],
  supply: ['admin', 'executive', 'supply_planner', 'sop_coordinator'],
  production_scheduling: ['admin', 'executive', 'supply_planner', 'sop_coordinator'],
  inventory: ['admin', 'executive', 'inventory_manager', 'supply_planner', 'sop_coordinator'],
  forecasting: ['admin', 'executive', 'demand_planner', 'supply_planner', 'finance_analyst', 'sop_coordinator'],
  scenarios: ['admin', 'executive', 'demand_planner', 'supply_planner', 'finance_analyst', 'sop_coordinator'],
  sop_cycle: ['admin', 'executive', 'sop_coordinator'],
  products: ['admin'],
}

// Action-level permissions: determines button visibility.
const PERMISSIONS: Record<Permission, UserRole[]> = {
  'demand.plan.write': ['admin', 'demand_planner', 'supply_planner', 'sop_coordinator'],
  'demand.plan.approve': ['admin', 'executive'],

  'supply.plan.write': ['admin', 'supply_planner', 'sop_coordinator'],
  'supply.plan.approve': ['admin', 'executive'],

  'scenario.write': ['admin', 'demand_planner', 'supply_planner', 'finance_analyst', 'sop_coordinator'],
  'scenario.approve': ['admin', 'executive'],

  'forecast.generate': ['admin', 'demand_planner', 'supply_planner', 'finance_analyst', 'sop_coordinator'],
  'forecast.consensus.approve': ['admin', 'executive', 'sop_coordinator'],

  'inventory.update': ['admin', 'inventory_manager', 'supply_planner'],
  'kpi.manage': ['admin', 'executive'],
  'products.manage': ['admin'],

  'sop.manage': ['admin', 'sop_coordinator'],
}

export function canAccessModule(role: UserRole | undefined | null, module: AppModule): boolean {
  if (!role) return false
  return MODULE_ACCESS[module].includes(role)
}

export function can(role: UserRole | undefined | null, permission: Permission): boolean {
  if (!role) return false
  return PERMISSIONS[permission].includes(role)
}
