from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from decimal import Decimal
from datetime import datetime
from typing import Literal, Dict, Any


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


EventSource = Literal["ERP", "MES", "IIOT", "QMS", "CMMS", "MANUAL"]
EventSeverity = Literal["low", "medium", "high", "critical"]


class CanonicalProductionEventIngestRequest(BaseModel):
    event_id: str
    event_type: str
    event_source: EventSource
    event_timestamp: datetime

    plant_id: Optional[str] = None
    line_id: Optional[str] = None
    resource_id: Optional[str] = None
    order_id: Optional[str] = None
    severity: EventSeverity = "medium"

    payload: Dict[str, Any] = {}
    correlation_id: Optional[str] = None
    trace_id: Optional[str] = None
    idempotency_key: Optional[str] = None


class CanonicalProductionEventResponse(BaseModel):
    event_id: str
    event_type: str
    event_source: EventSource
    event_timestamp: datetime
    processing_status: Literal["RECEIVED", "NORMALIZED", "PROCESSED", "FAILED", "REPLAYED"]
    duplicate: bool = False
    duplicate_of_event_id: Optional[str] = None
    replay_count: int = 0


class ProductionEventReplayResponse(BaseModel):
    event_id: str
    replay_count: int
    processing_status: Literal["REPLAYED", "FAILED", "PROCESSED", "NORMALIZED", "RECEIVED"]
    message: str
