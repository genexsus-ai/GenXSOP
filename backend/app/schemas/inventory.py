from pydantic import BaseModel
from typing import Optional, List
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
