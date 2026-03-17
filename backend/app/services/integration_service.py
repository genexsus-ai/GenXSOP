import json
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.product import Product, Category
from app.models.inventory import Inventory
from app.models.demand_plan import DemandPlan
from app.models.supply_plan import SupplyPlan
from app.models.production_event import ProductionEvent
from app.repositories.production_event_repository import ProductionEventRepository
from app.schemas.integration import (
    ERPProductSyncRequest,
    ERPInventorySyncRequest,
    ERPDemandActualSyncRequest,
    IntegrationOperationResponse,
    CanonicalProductionEventIngestRequest,
    CanonicalProductionEventResponse,
    ProductionEventReplayResponse,
)


class IntegrationService:
    """ERP/WMS integration scaffolding service.

    Current implementation is intentionally lightweight and synchronous,
    providing API contracts + basic persistence behavior for phased rollout.
    """

    def __init__(self, db: Session):
        self._db = db
        self._events = ProductionEventRepository(db)

    def sync_products(self, payload: ERPProductSyncRequest) -> IntegrationOperationResponse:
        created = 0
        updated = 0

        if payload.meta.dry_run:
            return IntegrationOperationResponse(
                success=True,
                source_system=payload.meta.source_system,
                batch_id=payload.meta.batch_id,
                processed=len(payload.items),
                dry_run=True,
                message="Dry run successful for product sync.",
            )

        for item in payload.items:
            product = self._db.query(Product).filter(Product.sku == item.sku).first()

            category_id = None
            if item.category_name:
                category = self._db.query(Category).filter(Category.name == item.category_name).first()
                if not category:
                    category = Category(name=item.category_name, level=0)
                    self._db.add(category)
                    self._db.flush()
                category_id = category.id

            if product:
                product.name = item.name
                if category_id is not None:
                    product.category_id = category_id
                if item.product_family is not None:
                    product.product_family = item.product_family
                if item.lead_time_days is not None:
                    product.lead_time_days = item.lead_time_days
                updated += 1
            else:
                self._db.add(
                    Product(
                        sku=item.sku,
                        name=item.name,
                        category_id=category_id,
                        product_family=item.product_family,
                        lead_time_days=item.lead_time_days or 0,
                        status="active",
                    )
                )
                created += 1

        self._db.commit()
        return IntegrationOperationResponse(
            success=True,
            source_system=payload.meta.source_system,
            batch_id=payload.meta.batch_id,
            processed=len(payload.items),
            created=created,
            updated=updated,
            dry_run=False,
            message="Product sync completed.",
        )

    def sync_inventory(self, payload: ERPInventorySyncRequest) -> IntegrationOperationResponse:
        created = 0
        updated = 0
        skipped = 0

        if payload.meta.dry_run:
            return IntegrationOperationResponse(
                success=True,
                source_system=payload.meta.source_system,
                batch_id=payload.meta.batch_id,
                processed=len(payload.items),
                dry_run=True,
                message="Dry run successful for inventory sync.",
            )

        for item in payload.items:
            product = self._db.query(Product).filter(Product.sku == item.sku).first()
            if not product:
                skipped += 1
                continue

            inv = (
                self._db.query(Inventory)
                .filter(Inventory.product_id == product.id, Inventory.location == item.location)
                .first()
            )
            if inv:
                inv.on_hand_qty = item.on_hand_qty
                inv.allocated_qty = item.allocated_qty
                inv.in_transit_qty = item.in_transit_qty
                inv.updated_at = datetime.utcnow()
                updated += 1
            else:
                self._db.add(
                    Inventory(
                        product_id=product.id,
                        location=item.location,
                        on_hand_qty=item.on_hand_qty,
                        allocated_qty=item.allocated_qty,
                        in_transit_qty=item.in_transit_qty,
                        safety_stock=0,
                        reorder_point=0,
                        status="normal",
                    )
                )
                created += 1

        self._db.commit()
        return IntegrationOperationResponse(
            success=True,
            source_system=payload.meta.source_system,
            batch_id=payload.meta.batch_id,
            processed=len(payload.items),
            created=created,
            updated=updated,
            skipped=skipped,
            dry_run=False,
            message="Inventory sync completed.",
        )

    def sync_demand_actuals(self, payload: ERPDemandActualSyncRequest) -> IntegrationOperationResponse:
        updated = 0
        skipped = 0

        if payload.meta.dry_run:
            return IntegrationOperationResponse(
                success=True,
                source_system=payload.meta.source_system,
                batch_id=payload.meta.batch_id,
                processed=len(payload.items),
                dry_run=True,
                message="Dry run successful for demand actual sync.",
            )

        for item in payload.items:
            product = self._db.query(Product).filter(Product.sku == item.sku).first()
            if not product:
                skipped += 1
                continue

            plan = (
                self._db.query(DemandPlan)
                .filter(
                    DemandPlan.product_id == product.id,
                    DemandPlan.period == item.period,
                    DemandPlan.region == item.region,
                    DemandPlan.channel == item.channel,
                )
                .order_by(DemandPlan.version.desc())
                .first()
            )
            if not plan:
                skipped += 1
                continue

            plan.actual_qty = item.actual_qty
            updated += 1

        self._db.commit()
        return IntegrationOperationResponse(
            success=True,
            source_system=payload.meta.source_system,
            batch_id=payload.meta.batch_id,
            processed=len(payload.items),
            updated=updated,
            skipped=skipped,
            dry_run=False,
            message="Demand actual sync completed.",
        )

    def publish_demand_plan(self, plan_id: int) -> IntegrationOperationResponse:
        plan = self._db.query(DemandPlan).filter(DemandPlan.id == plan_id).first()
        if not plan:
            return IntegrationOperationResponse(
                success=False,
                source_system="erp_publish",
                processed=1,
                skipped=1,
                message=f"Demand plan {plan_id} not found.",
            )
        if plan.status != "approved":
            return IntegrationOperationResponse(
                success=False,
                source_system="erp_publish",
                processed=1,
                skipped=1,
                message=f"Demand plan {plan_id} is not approved.",
            )
        return IntegrationOperationResponse(
            success=True,
            source_system="erp_publish",
            processed=1,
            message=f"Demand plan {plan_id} accepted for ERP publish pipeline.",
        )

    def publish_supply_plan(self, plan_id: int) -> IntegrationOperationResponse:
        plan = self._db.query(SupplyPlan).filter(SupplyPlan.id == plan_id).first()
        if not plan:
            return IntegrationOperationResponse(
                success=False,
                source_system="erp_publish",
                processed=1,
                skipped=1,
                message=f"Supply plan {plan_id} not found.",
            )
        if plan.status != "approved":
            return IntegrationOperationResponse(
                success=False,
                source_system="erp_publish",
                processed=1,
                skipped=1,
                message=f"Supply plan {plan_id} is not approved.",
            )
        return IntegrationOperationResponse(
            success=True,
            source_system="erp_publish",
            processed=1,
            message=f"Supply plan {plan_id} accepted for ERP publish pipeline.",
        )

    # ── Canonical Production Event Ingestion (Scope B) ─────────────────────

    def ingest_production_event(
        self,
        payload: CanonicalProductionEventIngestRequest,
    ) -> CanonicalProductionEventResponse:
        if payload.idempotency_key:
            existing_by_key = self._events.get_by_idempotency_key(payload.idempotency_key)
            if existing_by_key:
                return CanonicalProductionEventResponse(
                    event_id=existing_by_key.event_id,
                    event_type=existing_by_key.event_type,
                    event_source=existing_by_key.event_source,
                    event_timestamp=existing_by_key.event_timestamp,
                    processing_status=existing_by_key.processing_status,
                    duplicate=True,
                    duplicate_of_event_id=existing_by_key.event_id,
                    replay_count=existing_by_key.replay_count,
                )

        existing = self._events.get_by_event_id(payload.event_id)
        if existing:
            return CanonicalProductionEventResponse(
                event_id=existing.event_id,
                event_type=existing.event_type,
                event_source=existing.event_source,
                event_timestamp=existing.event_timestamp,
                processing_status=existing.processing_status,
                duplicate=True,
                duplicate_of_event_id=existing.event_id,
                replay_count=existing.replay_count,
            )

        normalized = self._normalize_event_payload(
            source=payload.event_source,
            event_type=payload.event_type,
            raw_payload=payload.payload,
        )

        row = ProductionEvent(
            event_id=payload.event_id,
            event_type=payload.event_type,
            event_source=payload.event_source,
            event_timestamp=payload.event_timestamp,
            plant_id=payload.plant_id,
            line_id=payload.line_id,
            resource_id=payload.resource_id,
            order_id=payload.order_id,
            severity=payload.severity,
            payload_json=json.dumps(payload.payload),
            normalized_json=json.dumps(normalized),
            correlation_id=payload.correlation_id,
            trace_id=payload.trace_id,
            idempotency_key=payload.idempotency_key,
            processing_status="NORMALIZED",
            processed_at=datetime.utcnow(),
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)

        return CanonicalProductionEventResponse(
            event_id=row.event_id,
            event_type=row.event_type,
            event_source=row.event_source,
            event_timestamp=row.event_timestamp,
            processing_status=row.processing_status,
            duplicate=False,
            duplicate_of_event_id=row.duplicate_of_event_id,
            replay_count=row.replay_count,
        )

    def replay_production_event(self, event_id: str) -> ProductionEventReplayResponse:
        row = self._events.get_by_event_id(event_id)
        if not row:
            return ProductionEventReplayResponse(
                event_id=event_id,
                replay_count=0,
                processing_status="FAILED",
                message=f"Event {event_id} not found.",
            )

        row.replay_count = int(row.replay_count or 0) + 1
        row.processing_status = "REPLAYED"
        row.processed_at = datetime.utcnow()
        row.last_error = None
        self._db.commit()
        self._db.refresh(row)

        return ProductionEventReplayResponse(
            event_id=row.event_id,
            replay_count=row.replay_count,
            processing_status=row.processing_status,
            message="Event replay accepted and marked as REPLAYED.",
        )

    def list_recent_events(self, limit: int = 100) -> list[CanonicalProductionEventResponse]:
        rows = self._events.list_recent(limit=limit)
        return [
            CanonicalProductionEventResponse(
                event_id=r.event_id,
                event_type=r.event_type,
                event_source=r.event_source,
                event_timestamp=r.event_timestamp,
                processing_status=r.processing_status,
                duplicate=bool(r.duplicate_of_event_id),
                duplicate_of_event_id=r.duplicate_of_event_id,
                replay_count=r.replay_count,
            )
            for r in rows
        ]

    def _normalize_event_payload(self, source: str, event_type: str, raw_payload: dict) -> dict:
        if source == "ERP":
            return self._normalize_erp_event(event_type, raw_payload)
        if source == "MES":
            return self._normalize_mes_event(event_type, raw_payload)
        if source == "IIOT":
            return self._normalize_iiot_event(event_type, raw_payload)
        if source == "QMS":
            return self._normalize_qms_event(event_type, raw_payload)
        if source == "CMMS":
            return self._normalize_cmms_event(event_type, raw_payload)
        return {"adapter": "MANUAL", "event_type": event_type, "payload": raw_payload}

    def _normalize_erp_event(self, event_type: str, payload: dict) -> dict:
        return {
            "adapter": "ERP",
            "event_type": event_type,
            "order_ref": payload.get("order_ref") or payload.get("order_id"),
            "priority": payload.get("priority"),
            "payload": payload,
        }

    def _normalize_mes_event(self, event_type: str, payload: dict) -> dict:
        return {
            "adapter": "MES",
            "event_type": event_type,
            "workcenter": payload.get("workcenter"),
            "line": payload.get("line"),
            "payload": payload,
        }

    def _normalize_iiot_event(self, event_type: str, payload: dict) -> dict:
        return {
            "adapter": "IIOT",
            "event_type": event_type,
            "sensor_id": payload.get("sensor_id"),
            "reading": payload.get("reading"),
            "payload": payload,
        }

    def _normalize_qms_event(self, event_type: str, payload: dict) -> dict:
        return {
            "adapter": "QMS",
            "event_type": event_type,
            "quality_lot": payload.get("lot") or payload.get("quality_lot"),
            "disposition": payload.get("disposition"),
            "payload": payload,
        }

    def _normalize_cmms_event(self, event_type: str, payload: dict) -> dict:
        return {
            "adapter": "CMMS",
            "event_type": event_type,
            "maintenance_ticket": payload.get("ticket") or payload.get("maintenance_ticket"),
            "asset": payload.get("asset") or payload.get("resource_id"),
            "payload": payload,
        }
