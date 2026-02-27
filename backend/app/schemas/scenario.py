from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal


class ScenarioBase(BaseModel):
    name: str
    description: Optional[str] = None
    scenario_type: str = "what_if"
    parameters: Dict[str, Any] = {}


class ScenarioCreate(ScenarioBase):
    pass


class ScenarioUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class ScenarioResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    scenario_type: str
    parameters: str
    results: Optional[str] = None
    revenue_impact: Optional[Decimal] = None
    margin_impact: Optional[Decimal] = None
    inventory_impact: Optional[Decimal] = None
    service_level_impact: Optional[Decimal] = None
    status: str
    created_by: Optional[int] = None
    approved_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScenarioListResponse(BaseModel):
    items: List[ScenarioResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ScenarioCompareRequest(BaseModel):
    scenario_ids: List[int]
