// ─────────────────────────────────────────────────────────────────────────────
// GenXSOP — TypeScript Domain Types
// ─────────────────────────────────────────────────────────────────────────────

// ── Auth / User ───────────────────────────────────────────────────────────────

export type UserRole =
  | 'admin'
  | 'executive'
  | 'demand_planner'
  | 'supply_planner'
  | 'inventory_manager'
  | 'finance_analyst'
  | 'sop_coordinator'
  | 'viewer'

export interface User {
  id: number
  email: string
  full_name: string
  role: UserRole
  department?: string
  is_active: boolean
  last_login?: string
  created_at: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: User
}

export interface RegisterRequest {
  email: string
  password: string
  full_name: string
  role?: UserRole
  department?: string
}

// ── Product / Category ────────────────────────────────────────────────────────

export interface Category {
  id: number
  name: string
  parent_id?: number
  level: number
  description?: string
  created_at: string
}

export interface Product {
  id: number
  sku: string
  name: string
  description?: string
  category_id?: number
  category?: Category
  product_family?: string
  unit_of_measure: string
  unit_cost?: number
  selling_price?: number
  lead_time_days: number
  min_order_qty: number
  status: 'active' | 'discontinued' | 'new'
  created_at: string
  updated_at: string
}

export interface CreateProductRequest {
  sku: string
  name: string
  description?: string
  category_id?: number
  product_family?: string
  unit_of_measure?: string
  unit_cost?: number
  selling_price?: number
  lead_time_days?: number
  min_order_qty?: number
  status?: 'active' | 'discontinued' | 'new'
}

// ── Demand Plan ───────────────────────────────────────────────────────────────

export type PlanStatus = 'draft' | 'submitted' | 'approved' | 'rejected' | 'locked'

export interface DemandPlan {
  id: number
  product_id: number
  product?: Product
  period: string
  region: string
  channel: string
  forecast_qty: number
  adjusted_qty?: number
  actual_qty?: number
  consensus_qty?: number
  confidence?: number
  notes?: string
  status: PlanStatus
  created_by?: number
  approved_by?: number
  version: number
  created_at: string
  updated_at: string
}

export interface CreateDemandPlanRequest {
  product_id: number
  period: string
  region?: string
  channel?: string
  forecast_qty: number
  adjusted_qty?: number
  consensus_qty?: number
  confidence?: number
  notes?: string
}

// ── Supply Plan ───────────────────────────────────────────────────────────────

export interface SupplyPlan {
  id: number
  product_id: number
  product?: Product
  period: string
  location: string
  planned_prod_qty?: number
  actual_prod_qty?: number
  capacity_max?: number
  capacity_used?: number
  supplier_name?: string
  lead_time_days?: number
  cost_per_unit?: number
  constraints?: string
  status: PlanStatus
  created_by?: number
  version: number
  created_at: string
  updated_at: string
}

export interface CreateSupplyPlanRequest {
  product_id: number
  period: string
  location?: string
  planned_prod_qty?: number
  capacity_max?: number
  supplier_name?: string
  lead_time_days?: number
  cost_per_unit?: number
  constraints?: string
}

// ── Inventory ─────────────────────────────────────────────────────────────────

export type InventoryStatus = 'normal' | 'low' | 'critical' | 'excess'

export interface Inventory {
  id: number
  product_id: number
  product?: Product
  location: string
  on_hand_qty: number
  allocated_qty: number
  in_transit_qty: number
  safety_stock: number
  reorder_point: number
  max_stock?: number
  days_of_supply?: number
  last_receipt_date?: string
  last_issue_date?: string
  valuation?: number
  status: InventoryStatus
  updated_at: string
}

export interface UpdateInventoryRequest {
  on_hand_qty?: number
  allocated_qty?: number
  in_transit_qty?: number
  safety_stock?: number
  reorder_point?: number
  max_stock?: number
}

// ── Forecast ──────────────────────────────────────────────────────────────────

export type ForecastModelType =
  | 'moving_average'
  | 'exp_smoothing'
  | 'prophet'

export interface Forecast {
  id: number
  product_id: number
  product?: Product
  model_type: ForecastModelType
  period: string
  predicted_qty: number
  lower_bound?: number
  upper_bound?: number
  confidence?: number
  mape?: number
  rmse?: number
  model_version?: string
  training_date?: string
  selection_reason?: string
  advisor_confidence?: number
  advisor_enabled?: boolean
  fallback_used?: boolean
  created_at: string
}

export interface GenerateForecastRequest {
  product_id: number
  model_type?: ForecastModelType
  horizon_months?: number
}

export interface ForecastAccuracy {
  product_id: number
  model_type: string
  mape: number
  wape: number
  bias: number
  rmse: number
  mae: number
  hit_rate: number
  period_count: number
  sample_count?: number
  avg_mape?: number
}

export interface ForecastDiagnostics {
  selected_model?: string
  selection_reason?: string
  advisor_confidence?: number
  advisor_enabled?: boolean
  fallback_used?: boolean
  warnings?: string[]
  history_months?: number
  candidate_metrics?: ForecastAccuracy[]
  data_quality_flags?: string[]
}

export interface GenerateForecastResponse {
  product_id: number
  model_type?: string | null
  horizon: number
  diagnostics?: ForecastDiagnostics
  forecasts: Array<{
    period: string
    predicted_qty: number
    lower_bound?: number | null
    upper_bound?: number | null
    confidence?: number | null
    mape?: number | null
    model_type?: string | null
  }>
}

// ── Scenario ──────────────────────────────────────────────────────────────────

export type ScenarioType = 'what_if' | 'best_case' | 'worst_case' | 'baseline'

export interface Scenario {
  id: number
  name: string
  description?: string
  scenario_type: ScenarioType
  parameters: Record<string, unknown>
  results?: Record<string, unknown>
  revenue_impact?: number
  margin_impact?: number
  inventory_impact?: number
  service_level_impact?: number
  status: PlanStatus
  created_by?: number
  approved_by?: number
  created_at: string
  updated_at: string
}

export interface CreateScenarioRequest {
  name: string
  description?: string
  scenario_type?: ScenarioType
  parameters: Record<string, unknown>
}

// ── S&OP Cycle ────────────────────────────────────────────────────────────────

export type SOPStepStatus = 'pending' | 'in_progress' | 'completed' | 'skipped'
export type SOPCycleStatus = 'active' | 'completed' | 'cancelled'

export interface SOPCycle {
  id: number
  cycle_name: string
  period: string
  current_step: number
  step_1_status: SOPStepStatus
  step_1_due_date?: string
  step_1_owner_id?: number
  step_2_status: SOPStepStatus
  step_2_due_date?: string
  step_2_owner_id?: number
  step_3_status: SOPStepStatus
  step_3_due_date?: string
  step_3_owner_id?: number
  step_4_status: SOPStepStatus
  step_4_due_date?: string
  step_4_owner_id?: number
  step_5_status: SOPStepStatus
  step_5_due_date?: string
  step_5_owner_id?: number
  decisions?: string
  action_items?: string
  notes?: string
  overall_status: SOPCycleStatus
  created_at: string
  updated_at: string
}

export interface CreateSOPCycleRequest {
  cycle_name: string
  period: string
  step_1_due_date?: string
  step_2_due_date?: string
  step_3_due_date?: string
  step_4_due_date?: string
  step_5_due_date?: string
  notes?: string
}

// ── KPI ───────────────────────────────────────────────────────────────────────

export type KPICategory = 'demand' | 'supply' | 'inventory' | 'financial' | 'service'
export type KPITrend = 'improving' | 'declining' | 'stable'

export interface KPIMetric {
  id: number
  metric_name: string
  metric_category: KPICategory
  period: string
  value: number
  target?: number
  previous_value?: number
  variance?: number
  variance_pct?: number
  trend?: KPITrend
  unit?: string
  created_at: string
}

export interface CreateKPIRequest {
  metric_name: string
  metric_category: KPICategory
  period: string
  value: number
  target?: number
  previous_value?: number
  unit?: string
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

export interface DashboardSummary {
  total_products: number
  active_demand_plans: number
  active_supply_plans: number
  inventory_alerts: number
  pending_approvals: number
  active_sop_cycles: number
  total_inventory_value: number
  forecast_accuracy: number
  forecast_accuracy_change?: number
  otif_rate: number
  otif_change?: number
  low_stock_count: number
  active_sop_cycle?: string
  sop_cycle_stage?: string
  demand_plans_count: number
  supply_plans_count: number
  open_scenarios_count: number
  products_count: number
  recent_activity: Array<{
    description: string
    status: string
    created_at: string
  }>
}

export interface DashboardAlert {
  id: string
  type: 'critical' | 'warning' | 'info'
  severity: 'critical' | 'warning' | 'info'
  title: string
  message: string
  entity_type?: string
  entity_id?: number
  created_at: string
}

// ── Pagination ────────────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface PaginationParams {
  page?: number
  page_size?: number
}

// ── API Error ─────────────────────────────────────────────────────────────────

export interface ApiError {
  code: string
  message: string
  details?: Array<{ field: string; message: string }>
}

// ── UI ────────────────────────────────────────────────────────────────────────

export interface Notification {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message?: string
  duration?: number
}

export interface SelectOption {
  value: string | number
  label: string
}

export interface TableColumn<T> {
  key: keyof T | string
  header: string
  sortable?: boolean
  render?: (value: unknown, row: T) => React.ReactNode
  className?: string
}
