from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal


class DemandPlanBase(BaseModel):
    product_id: int
    period: date
    region: str = "Global"
    channel: str = "All"
    forecast_qty: Decimal
    adjusted_qty: Optional[Decimal] = None
    actual_qty: Optional[Decimal] = None
    consensus_qty: Optional[Decimal] = None
    confidence: Optional[Decimal] = None
    notes: Optional[str] = None


class DemandPlanCreate(DemandPlanBase):
    pass


class DemandPlanUpdate(BaseModel):
    forecast_qty: Optional[Decimal] = None
    adjusted_qty: Optional[Decimal] = None
    actual_qty: Optional[Decimal] = None
    consensus_qty: Optional[Decimal] = None
    confidence: Optional[Decimal] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class DemandPlanResponse(DemandPlanBase):
    id: int
    status: str
    created_by: Optional[int] = None
    approved_by: Optional[int] = None
    version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DemandPlanListResponse(BaseModel):
    items: List[DemandPlanResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AdjustmentRequest(BaseModel):
    adjusted_qty: Decimal
    notes: Optional[str] = None


class ApprovalRequest(BaseModel):
    comments: Optional[str] = None
