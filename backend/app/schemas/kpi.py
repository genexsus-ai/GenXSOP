from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal


class KPIMetricBase(BaseModel):
    metric_name: str
    metric_category: str
    period: date
    value: Decimal
    target: Optional[Decimal] = None
    previous_value: Optional[Decimal] = None
    unit: Optional[str] = None


class KPIMetricCreate(KPIMetricBase):
    pass


class KPIMetricResponse(KPIMetricBase):
    id: int
    variance: Optional[Decimal] = None
    variance_pct: Optional[Decimal] = None
    trend: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class KPIMetricListResponse(BaseModel):
    items: List[KPIMetricResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class KPIDashboardData(BaseModel):
    demand_kpis: List[KPIMetricResponse]
    supply_kpis: List[KPIMetricResponse]
    inventory_kpis: List[KPIMetricResponse]
    service_kpis: List[KPIMetricResponse]
    financial_kpis: List[KPIMetricResponse]


class KPITargetRequest(BaseModel):
    metric_name: str
    target: Decimal
