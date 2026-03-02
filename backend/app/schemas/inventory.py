from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal


class InventoryBase(BaseModel):
    product_id: int
    location: str = "Main"
    on_hand_qty: Decimal = Decimal("0")
    allocated_qty: Decimal = Decimal("0")
    in_transit_qty: Decimal = Decimal("0")
    safety_stock: Decimal = Decimal("0")
    reorder_point: Decimal = Decimal("0")
    max_stock: Optional[Decimal] = None
    days_of_supply: Optional[Decimal] = None
    last_receipt_date: Optional[date] = None
    last_issue_date: Optional[date] = None
    valuation: Optional[Decimal] = None
    status: str = "normal"


class InventoryUpdate(BaseModel):
    on_hand_qty: Optional[Decimal] = None
    allocated_qty: Optional[Decimal] = None
    in_transit_qty: Optional[Decimal] = None
    safety_stock: Optional[Decimal] = None
    reorder_point: Optional[Decimal] = None
    max_stock: Optional[Decimal] = None
    last_receipt_date: Optional[date] = None
    last_issue_date: Optional[date] = None


class InventoryPolicyOverride(BaseModel):
    safety_stock: Optional[Decimal] = None
    reorder_point: Optional[Decimal] = None
    max_stock: Optional[Decimal] = None
    reason: str = Field(..., min_length=3, max_length=500)


class InventoryOptimizationRunRequest(BaseModel):
    product_id: Optional[int] = None
    location: Optional[str] = None
    service_level_target: float = Field(0.95, ge=0.80, le=0.999)
    lead_time_days: int = Field(14, ge=1, le=365)
    review_period_days: int = Field(7, ge=1, le=90)
    moq_units: Optional[Decimal] = Field(None, ge=0)
    lot_size_units: Optional[Decimal] = Field(None, ge=0)
    capacity_max_units: Optional[Decimal] = Field(None, ge=0)
    lead_time_variability_days: Optional[Decimal] = Field(None, ge=0)


class InventoryExceptionView(BaseModel):
    id: Optional[int] = None
    inventory_id: int
    product_id: int
    location: str
    exception_type: str
    severity: str
    status: str
    recommended_action: str
    owner_user_id: Optional[int] = None
    due_date: Optional[date] = None
    notes: Optional[str] = None


class InventoryExceptionUpdateRequest(BaseModel):
    owner_user_id: Optional[int] = None
    due_date: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=1000)
    status: Optional[str] = Field(None, pattern="^(open|in_progress|resolved|dismissed)$")


class InventoryRecommendationGenerateRequest(BaseModel):
    product_id: Optional[int] = None
    location: Optional[str] = None
    min_confidence: float = Field(0.55, ge=0.0, le=1.0)
    max_items: int = Field(100, ge=1, le=500)
    enforce_quality_gate: bool = True
    min_quality_score: float = Field(0.60, ge=0.0, le=1.0)


class InventoryPolicyRecommendationView(BaseModel):
    id: int
    inventory_id: int
    product_id: int
    location: str
    recommended_safety_stock: Decimal
    recommended_reorder_point: Decimal
    recommended_max_stock: Optional[Decimal] = None
    confidence_score: Decimal
    rationale: str
    signals: Optional[Dict[str, Any]] = None
    status: str
    decision_notes: Optional[str] = None
    decided_by: Optional[int] = None
    decided_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class InventoryRecommendationDecisionRequest(BaseModel):
    decision: str = Field(..., pattern="^(accepted|rejected)$")
    apply_changes: bool = True
    notes: Optional[str] = Field(None, max_length=1000)


class InventoryRecommendationApproveRequest(BaseModel):
    notes: Optional[str] = Field(None, max_length=1000)


class InventoryAutoApplyRequest(BaseModel):
    min_confidence: float = Field(0.80, ge=0.0, le=1.0)
    max_demand_pressure: float = Field(1.20, ge=0.0, le=10.0)
    max_items: int = Field(100, ge=1, le=1000)
    min_quality_score: float = Field(0.60, ge=0.0, le=1.0)
    dry_run: bool = False


class InventoryAutoApplyResponse(BaseModel):
    eligible_count: int
    applied_count: int
    skipped_count: int
    recommendation_ids: List[int]


class InventoryRebalanceRecommendationView(BaseModel):
    product_id: int
    product_name: Optional[str] = None
    from_inventory_id: int
    from_location: str
    to_inventory_id: int
    to_location: str
    transfer_qty: Decimal
    estimated_service_uplift_pct: float


class InventoryControlTowerSummary(BaseModel):
    pending_recommendations: int
    accepted_recommendations: int
    applied_recommendations: int
    acceptance_rate_pct: float
    autonomous_applied_24h: int
    open_exceptions: int
    overdue_exceptions: int
    recommendation_backlog_risk: str


class InventoryDataQualityView(BaseModel):
    inventory_id: int
    product_id: int
    location: str
    completeness_score: float
    freshness_score: float
    consistency_score: float
    overall_score: float
    quality_tier: str


class InventoryEscalationItem(BaseModel):
    exception_id: int
    inventory_id: int
    product_id: int
    location: str
    severity: str
    status: str
    owner_user_id: Optional[int] = None
    due_date: Optional[date] = None
    escalation_level: str
    escalation_reason: str


class InventoryWorkingCapitalSummary(BaseModel):
    total_inventory_value: Decimal
    estimated_carrying_cost_annual: Decimal
    estimated_carrying_cost_monthly: Decimal
    excess_inventory_value: Decimal
    low_stock_exposure_value: Decimal
    inventory_health_index: float


class InventoryAssessmentAreaScore(BaseModel):
    area: str
    yes_count: int
    total_count: int
    score_0_to_3: int
    rag: str


class InventoryAssessmentScorecard(BaseModel):
    total_yes: int
    total_checks: int
    maturity_level: str
    areas: List[InventoryAssessmentAreaScore]


class InventoryServiceLevelAnalyticsRequest(BaseModel):
    inventory_id: Optional[int] = None
    product_id: Optional[int] = None
    location: Optional[str] = None
    target_service_level: float = Field(0.95, ge=0.50, le=0.999)
    method: str = Field("analytical", pattern="^(analytical|monte_carlo)$")
    simulation_runs: int = Field(5000, ge=100, le=50000)
    demand_std_override: Optional[float] = Field(None, ge=0)
    lead_time_std_override: Optional[float] = Field(None, ge=0)
    bucket_count: int = Field(20, ge=5, le=50)


class InventoryServiceLevelDistributionPoint(BaseModel):
    bucket: str
    midpoint: float
    probability: float


class InventoryServiceLevelSuggestion(BaseModel):
    target_service_level: float
    required_safety_stock: Decimal
    required_reorder_point: Decimal


class InventoryServiceLevelAnalyticsResponse(BaseModel):
    inventory_id: int
    product_id: int
    location: str
    method: str
    target_service_level: float
    current_on_hand_qty: Decimal
    current_safety_stock: Decimal
    current_reorder_point: Decimal
    demand_mean_daily: Decimal
    demand_std_daily: Decimal
    lead_time_mean_days: Decimal
    lead_time_std_days: Decimal
    mean_demand_during_lead_time: Decimal
    std_demand_during_lead_time: Decimal
    cycle_service_level: float
    fill_rate: float
    stockout_probability: float
    expected_shortage_units: Decimal
    recommended_safety_stock: Decimal
    recommended_reorder_point: Decimal
    service_level_curve: List[InventoryServiceLevelSuggestion]
    distribution: List[InventoryServiceLevelDistributionPoint]


class InventoryOptimizationRunResponse(BaseModel):
    run_id: str
    processed_count: int
    updated_count: int
    exception_count: int
    generated_at: datetime
    exceptions: List[InventoryExceptionView]


class InventoryResponse(InventoryBase):
    id: int
    updated_at: datetime

    class Config:
        from_attributes = True


class InventoryListResponse(BaseModel):
    items: List[InventoryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class InventoryHealthSummary(BaseModel):
    total_products: int
    normal_count: int
    low_count: int
    critical_count: int
    excess_count: int
    total_value: Decimal
    normal_pct: float
    low_pct: float
    critical_pct: float
    excess_pct: float
