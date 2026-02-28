from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, Field


class ProductionScheduleGenerateRequest(BaseModel):
    supply_plan_id: int
    workcenters: List[str] = Field(default_factory=lambda: ["WC-1"])
    lines: List[str] = Field(default_factory=lambda: ["Line-1"])
    shifts: List[str] = Field(default_factory=lambda: ["Shift-A", "Shift-B"])
    duration_hours_per_slot: int = Field(default=8, ge=1, le=24)


class ProductionScheduleStatusUpdateRequest(BaseModel):
    status: str


class ProductionScheduleResequenceRequest(BaseModel):
    direction: str = Field(pattern="^(up|down)$")


class CapacityGroupSummary(BaseModel):
    workcenter: str
    line: str
    shift: str
    slot_count: int
    total_planned_qty: Decimal


class ProductionCapacitySummaryResponse(BaseModel):
    supply_plan_id: int
    slot_count: int
    planned_total_qty: Decimal
    capacity_max_qty: Optional[Decimal] = None
    utilization_pct: float
    overloaded: bool
    groups: List[CapacityGroupSummary]


class ProductionScheduleResponse(BaseModel):
    id: int
    supply_plan_id: int
    product_id: int
    period: date
    workcenter: str
    line: str
    shift: str
    sequence_order: int
    planned_qty: Decimal
    planned_start_at: datetime
    planned_end_at: datetime
    status: str
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
