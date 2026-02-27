from datetime import datetime
from sqlalchemy.orm import Session

from app.models.product import Product, Category
from app.models.inventory import Inventory
from app.models.demand_plan import DemandPlan
from app.models.supply_plan import SupplyPlan
from app.schemas.integration import (
    ERPProductSyncRequest,
    ERPInventorySyncRequest,
    ERPDemandActualSyncRequest,
    IntegrationOperationResponse,
)


class IntegrationService:
    """ERP/WMS integration scaffolding service.

    Current implementation is intentionally lightweight and synchronous,
    providing API contracts + basic persistence behavior for phased rollout.
    """

    def __init__(self, db: Session):
        self._db = db

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
