from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal


class SupplyPlanBase(BaseModel):
    product_id: int
    period: date
    location: str = "Main"
    planned_prod_qty: Optional[Decimal] = None
    actual_prod_qty: Optional[Decimal] = None
    capacity_max: Optional[Decimal] = None
    capacity_used: Optional[Decimal] = None
    supplier_name: Optional[str] = None
    lead_time_days: Optional[int] = None
    cost_per_unit: Optional[Decimal] = None
    constraints: Optional[str] = None


class SupplyPlanCreate(SupplyPlanBase):
    pass


class SupplyPlanUpdate(BaseModel):
    planned_prod_qty: Optional[Decimal] = None
    actual_prod_qty: Optional[Decimal] = None
    capacity_max: Optional[Decimal] = None
    capacity_used: Optional[Decimal] = None
    supplier_name: Optional[str] = None
    lead_time_days: Optional[int] = None
    cost_per_unit: Optional[Decimal] = None
    constraints: Optional[str] = None
    status: Optional[str] = None


class SupplyPlanResponse(SupplyPlanBase):
    id: int
    status: str
    created_by: Optional[int] = None
    version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SupplyPlanListResponse(BaseModel):
    items: List[SupplyPlanResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class GapAnalysisItem(BaseModel):
    product_id: int
    product_name: str
    sku: str
    period: date
    demand_qty: Decimal
    supply_qty: Decimal
    gap: Decimal
    gap_pct: float
    status: str
