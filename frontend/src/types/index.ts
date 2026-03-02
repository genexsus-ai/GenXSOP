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

export interface SupplyGapAnalysisItem {
  product_id: number
  product_name: string
  sku: string
  period: string
  consensus_demand_qty: number
  demand_qty: number
  planned_production_qty: number
  actual_production_qty: number
  planned_supply_qty: number
  inventory_available_qty: number
  effective_supply_qty: number
  additional_prod_required_qty: number
  plan_gap_qty: number
  plan_gap_pct: number
  actual_gap_qty: number
  actual_gap_pct: number
  coverage_gap_qty: number
  coverage_gap_pct: number
  supply_qty: number
  gap: number
  gap_pct: number
  status: string
}

// ── Production Scheduling ────────────────────────────────────────────────────

export type ProductionScheduleStatus = 'draft' | 'released' | 'in_progress' | 'completed'

export interface ProductionSchedule {
  id: number
  supply_plan_id: number
  product_id: number
  period: string
  workcenter: string
  line: string
  shift: string
  sequence_order: number
  planned_qty: number
  planned_start_at: string
  planned_end_at: string
  status: ProductionScheduleStatus
  created_by?: number
  created_at: string
  updated_at: string
}

export interface GenerateProductionScheduleRequest {
  supply_plan_id: number
  workcenters: string[]
  lines: string[]
  shifts: string[]
  duration_hours_per_slot?: number
}

export interface ProductionCapacityGroupSummary {
  workcenter: string
  line: string
  shift: string
  slot_count: number
  total_planned_qty: number
}

export interface ProductionCapacitySummary {
  supply_plan_id: number
  slot_count: number
  planned_total_qty: number
  capacity_max_qty?: number
  utilization_pct: number
  overloaded: boolean
  groups: ProductionCapacityGroupSummary[]
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

export interface InventoryOptimizationRunRequest {
  product_id?: number
  location?: string
  service_level_target?: number
  lead_time_days?: number
  review_period_days?: number
  moq_units?: number
  lot_size_units?: number
  capacity_max_units?: number
  lead_time_variability_days?: number
}

export interface InventoryException {
  id?: number
  inventory_id: number
  product_id: number
  location: string
  exception_type: 'stockout_risk' | 'excess_risk' | string
  severity: 'high' | 'medium' | 'low' | string
  status: string
  recommended_action: string
  owner_user_id?: number
  due_date?: string
  notes?: string
}

export interface InventoryOptimizationRunResponse {
  run_id: string
  processed_count: number
  updated_count: number
  exception_count: number
  generated_at: string
  exceptions: InventoryException[]
}

export interface InventoryPolicyOverrideRequest {
  safety_stock?: number
  reorder_point?: number
  max_stock?: number
  reason: string
}

export interface InventoryExceptionUpdateRequest {
  owner_user_id?: number
  due_date?: string
  notes?: string
  status?: 'open' | 'in_progress' | 'resolved' | 'dismissed'
}

export interface InventoryRecommendationGenerateRequest {
  product_id?: number
  location?: string
  min_confidence?: number
  max_items?: number
  enforce_quality_gate?: boolean
  min_quality_score?: number
}

export interface InventoryPolicyRecommendation {
  id: number
  inventory_id: number
  product_id: number
  location: string
  recommended_safety_stock: number
  recommended_reorder_point: number
  recommended_max_stock?: number
  confidence_score: number
  rationale: string
  signals?: Record<string, unknown>
  status: 'pending' | 'accepted' | 'rejected' | 'applied' | string
  decision_notes?: string
  decided_by?: number
  decided_at?: string
  created_at: string
  updated_at: string
}

export interface InventoryRecommendationDecisionRequest {
  decision: 'accepted' | 'rejected'
  apply_changes?: boolean
  notes?: string
}

export interface InventoryRecommendationApproveRequest {
  notes?: string
}

export interface InventoryAutoApplyRequest {
  min_confidence?: number
  max_demand_pressure?: number
  max_items?: number
  min_quality_score?: number
  dry_run?: boolean
}

export interface InventoryAutoApplyResponse {
  eligible_count: number
  applied_count: number
  skipped_count: number
  recommendation_ids: number[]
}

export interface InventoryRebalanceRecommendation {
  product_id: number
  product_name?: string
  from_inventory_id: number
  from_location: string
  to_inventory_id: number
  to_location: string
  transfer_qty: number
  estimated_service_uplift_pct: number
}

export interface InventoryControlTowerSummary {
  pending_recommendations: number
  accepted_recommendations: number
  applied_recommendations: number
  acceptance_rate_pct: number
  autonomous_applied_24h: number
  open_exceptions: number
  overdue_exceptions: number
  recommendation_backlog_risk: 'low' | 'medium' | 'high' | string
}

export interface InventoryDataQuality {
  inventory_id: number
  product_id: number
  location: string
  completeness_score: number
  freshness_score: number
  consistency_score: number
  overall_score: number
  quality_tier: 'low' | 'medium' | 'high' | string
}

export interface InventoryEscalationItem {
  exception_id: number
  inventory_id: number
  product_id: number
  location: string
  severity: string
  status: string
  owner_user_id?: number
  due_date?: string
  escalation_level: string
  escalation_reason: string
}

export interface InventoryWorkingCapitalSummary {
  total_inventory_value: number
  estimated_carrying_cost_annual: number
  estimated_carrying_cost_monthly: number
  excess_inventory_value: number
  low_stock_exposure_value: number
  inventory_health_index: number
}

export interface InventoryHealthSummary {
  total_products: number
  normal_count: number
  low_count: number
  critical_count: number
  excess_count: number
  total_value: number
  normal_pct: number
  low_pct: number
  critical_pct: number
  excess_pct: number
}

export interface InventoryAssessmentAreaScore {
  area: string
  yes_count: number
  total_count: number
  score_0_to_3: number
  rag: 'green' | 'amber' | 'red' | string
}

export interface InventoryAssessmentScorecard {
  total_yes: number
  total_checks: number
  maturity_level: string
  areas: InventoryAssessmentAreaScore[]
}

// ── Forecast ──────────────────────────────────────────────────────────────────

export type ForecastModelType =
  | 'moving_average'
  | 'ewma'
  | 'exp_smoothing'
  | 'seasonal_naive'
  | 'arima'
  | 'prophet'
  | 'lstm'

export interface Forecast {
  id: number
  product_id: number
  product?: Product
  model_type: ForecastModelType
  run_audit_id?: number
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
  model_params?: Record<string, unknown>
  warnings?: string[]
  created_at: string
}

export interface GenerateForecastRequest {
  product_id: number
  model_type?: ForecastModelType
  horizon_months?: number
  model_params?: Record<string, unknown>
}

export interface ForecastAccuracy {
  product_id: number
  model_type: string
  mape: number
  smape: number
  wape: number
  bias: number
  rmse: number
  nrmse_pct: number
  mae: number
  mdae: number
  r2: number
  hit_rate: number
  period_count: number
  sample_count?: number
  avg_mape?: number
}

export interface ForecastDiagnostics {
  selected_model?: string
  run_audit_id?: number
  selection_reason?: string
  advisor_confidence?: number
  advisor_enabled?: boolean
  fallback_used?: boolean
  selected_model_params?: Record<string, unknown>
  warnings?: string[]
  history_months?: number
  candidate_metrics?: ForecastAccuracy[]
  data_quality_flags?: string[]
}

export interface ForecastDriftAlert {
  product_id: number
  model_type: string
  previous_mape: number
  recent_mape: number
  degradation_pct: number
  severity: 'medium' | 'high'
}

export interface ForecastModelComparisonItem {
  rank: number
  model_type: string
  mape: number
  smape: number
  wape: number
  rmse: number
  nrmse_pct: number
  mae: number
  mdae: number
  r2: number
  bias: number
  hit_rate: number
  period_count: number
  score: number
  model_params?: Record<string, unknown>
  best_params?: Record<string, unknown>
  parameter_results?: Array<{
    model_type: string
    model_params?: Record<string, unknown>
    mape: number
    smape: number
    wape: number
    rmse: number
    nrmse_pct: number
    mae: number
    mdae: number
    r2: number
    bias: number
    hit_rate: number
    period_count: number
    score: number
  }>
  series?: Array<{
    period: string
    actual_qty: number
    predicted_qty: number
  }>
}

export interface ForecastModelComparisonResponse {
  product_id: number
  history_months: number
  test_months: number
  min_train_months: number
  models: ForecastModelComparisonItem[]
  parameter_grid_used?: Record<string, Array<Record<string, unknown>>>
  data_quality_flags: string[]
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

export interface ForecastRecommendationResponse {
  product_id: number
  diagnostics?: ForecastDiagnostics
}

export interface ForecastPromoteResponse {
  product_id: number
  selected_model: ForecastModelType
  records_promoted: number
  periods: string[]
}

export type ForecastConsensusStatus = 'draft' | 'proposed' | 'approved' | 'frozen'

export interface ForecastConsensus {
  id: number
  forecast_run_audit_id?: number | null
  product_id: number
  period: string
  baseline_qty: number
  sales_override_qty: number
  marketing_uplift_qty: number
  finance_adjustment_qty: number
  constraint_cap_qty?: number | null
  pre_consensus_qty: number
  final_consensus_qty: number
  status: ForecastConsensusStatus
  notes?: string | null
  approved_by?: number | null
  approved_at?: string | null
  version: number
  created_by?: number | null
  created_at: string
  updated_at: string
}

export interface CreateForecastConsensusRequest {
  forecast_run_audit_id: number
  product_id: number
  period: string
  baseline_qty: number
  sales_override_qty?: number
  marketing_uplift_qty?: number
  finance_adjustment_qty?: number
  constraint_cap_qty?: number | null
  status?: ForecastConsensusStatus
  notes?: string
}

export interface UpdateForecastConsensusRequest {
  baseline_qty?: number
  sales_override_qty?: number
  marketing_uplift_qty?: number
  finance_adjustment_qty?: number
  constraint_cap_qty?: number | null
  status?: ForecastConsensusStatus
  notes?: string
}

export interface ApproveForecastConsensusRequest {
  notes?: string
}

// ── Scenario ──────────────────────────────────────────────────────────────────

export type ScenarioType = 'what_if' | 'baseline' | 'stress_test' | 'best_case' | 'worst_case'
export type ScenarioStatus = 'draft' | 'submitted' | 'completed' | 'approved' | 'rejected'

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
  status: ScenarioStatus
  created_by?: number
  approved_by?: number
  created_at: string
  updated_at: string
}

export interface ScenarioTradeoffSummary {
  scenario_id: number
  status: string
  period?: string
  message?: string
  tradeoff?: {
    inventory_carrying_cost: number
    stockout_penalty_cost: number
    working_capital_delta: number
    composite_score: number
    open_inventory_exceptions: number
    high_risk_exception_count: number
  } | null
  service_level?: {
    baseline: number
    scenario: number
    delta: number
  }
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

export interface SOPExecutiveScorecard {
  cycle_id: number
  cycle_name: string
  period: string
  scenario_reference?: string
  service: {
    baseline_service_level: number
    scenario_service_level: number
    delta_service_level: number
  }
  cost: {
    inventory_carrying_cost: number
    stockout_penalty_cost: number
    composite_tradeoff_score: number
  }
  cash: {
    working_capital_delta: number
    inventory_value_estimate: number
  }
  risk: {
    open_exceptions: number
    high_risk_exceptions: number
    pending_recommendations: number
    backlog_risk: 'low' | 'medium' | 'high' | string
  }
  decision_signal: 'recommended' | 'review_required' | 'not_recommended' | string
}

export interface CreateSOPCycleRequest {
  cycle_name: string
  period: string
  step_1_due_date?: string
  step_1_owner_id?: number
  step_2_due_date?: string
  step_2_owner_id?: number
  step_3_due_date?: string
  step_3_owner_id?: number
  step_4_due_date?: string
  step_4_owner_id?: number
  step_5_due_date?: string
  step_5_owner_id?: number
  notes?: string
}

export interface UpdateSOPCycleRequest {
  cycle_name?: string
  period?: string
  step_1_due_date?: string
  step_1_owner_id?: number
  step_2_due_date?: string
  step_2_owner_id?: number
  step_3_due_date?: string
  step_3_owner_id?: number
  step_4_due_date?: string
  step_4_owner_id?: number
  step_5_due_date?: string
  step_5_owner_id?: number
  decisions?: string
  action_items?: string
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
