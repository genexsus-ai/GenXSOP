from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date


class SOPCycleBase(BaseModel):
    cycle_name: str
    period: date
    step_1_due_date: Optional[date] = None
    step_1_owner_id: Optional[int] = None
    step_2_due_date: Optional[date] = None
    step_2_owner_id: Optional[int] = None
    step_3_due_date: Optional[date] = None
    step_3_owner_id: Optional[int] = None
    step_4_due_date: Optional[date] = None
    step_4_owner_id: Optional[int] = None
    step_5_due_date: Optional[date] = None
    step_5_owner_id: Optional[int] = None
    notes: Optional[str] = None


class SOPCycleCreate(SOPCycleBase):
    pass


class SOPCycleUpdate(BaseModel):
    cycle_name: Optional[str] = None
    notes: Optional[str] = None
    decisions: Optional[str] = None
    action_items: Optional[str] = None


class SOPCycleResponse(SOPCycleBase):
    id: int
    current_step: int
    step_1_status: str
    step_2_status: str
    step_3_status: str
    step_4_status: str
    step_5_status: str
    decisions: Optional[str] = None
    action_items: Optional[str] = None
    overall_status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SOPCycleListResponse(BaseModel):
    items: List[SOPCycleResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
