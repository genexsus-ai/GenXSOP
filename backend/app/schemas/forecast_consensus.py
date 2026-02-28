from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class ForecastConsensusBase(BaseModel):
    forecast_run_audit_id: int
    product_id: int
    period: date
    baseline_qty: Decimal
    sales_override_qty: Decimal = Decimal("0")
    marketing_uplift_qty: Decimal = Decimal("0")
    finance_adjustment_qty: Decimal = Decimal("0")
    constraint_cap_qty: Optional[Decimal] = None
    notes: Optional[str] = None


class ForecastConsensusCreate(ForecastConsensusBase):
    status: str = "draft"


class ForecastConsensusUpdate(BaseModel):
    baseline_qty: Optional[Decimal] = None
    sales_override_qty: Optional[Decimal] = None
    marketing_uplift_qty: Optional[Decimal] = None
    finance_adjustment_qty: Optional[Decimal] = None
    constraint_cap_qty: Optional[Decimal] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class ForecastConsensusApproveRequest(BaseModel):
    notes: Optional[str] = None


class ForecastConsensusResponse(BaseModel):
    id: int
    forecast_run_audit_id: Optional[int] = None
    product_id: int
    period: date
    baseline_qty: Decimal
    sales_override_qty: Decimal
    marketing_uplift_qty: Decimal
    finance_adjustment_qty: Decimal
    constraint_cap_qty: Optional[Decimal] = None
    pre_consensus_qty: Decimal
    final_consensus_qty: Decimal
    status: str
    notes: Optional[str] = None
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    version: int
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
