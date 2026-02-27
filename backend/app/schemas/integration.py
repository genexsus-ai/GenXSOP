from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from decimal import Decimal


class IntegrationRequestMeta(BaseModel):
    source_system: str
    batch_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    dry_run: bool = False


class ERPProductItem(BaseModel):
    sku: str
    name: str
    category_name: Optional[str] = None
    product_family: Optional[str] = None
    lead_time_days: Optional[int] = None


class ERPInventoryItem(BaseModel):
    sku: str
    location: str
    on_hand_qty: Decimal
    allocated_qty: Decimal = Decimal("0")
    in_transit_qty: Decimal = Decimal("0")


class ERPDemandActualItem(BaseModel):
    sku: str
    period: date
    actual_qty: Decimal
    region: str = "Global"
    channel: str = "All"


class ERPProductSyncRequest(BaseModel):
    meta: IntegrationRequestMeta
    items: List[ERPProductItem]


class ERPInventorySyncRequest(BaseModel):
    meta: IntegrationRequestMeta
    items: List[ERPInventoryItem]


class ERPDemandActualSyncRequest(BaseModel):
    meta: IntegrationRequestMeta
    items: List[ERPDemandActualItem]


class IntegrationOperationResponse(BaseModel):
    success: bool
    source_system: str
    batch_id: Optional[str] = None
    processed: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    dry_run: bool = False
    message: str
