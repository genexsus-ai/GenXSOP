from datetime import date

from app.models.product import Category, Product
from app.models.inventory import Inventory
from app.models.demand_plan import DemandPlan
from app.models.supply_plan import SupplyPlan
from app.services.integration_service import IntegrationService
from app.schemas.integration import (
    ERPProductSyncRequest,
    ERPInventorySyncRequest,
    ERPDemandActualSyncRequest,
)


def _seed_product(db, sku: str = "SKU-ERP-1") -> Product:
    category = Category(name="Electronics", level=0)
    db.add(category)
    db.flush()

    product = Product(
        sku=sku,
        name="Seed Product",
        category_id=category.id,
        selling_price=100,
        unit_cost=50,
        lead_time_days=7,
        status="active",
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def test_sync_products_dry_run(db):
    service = IntegrationService(db)
    payload = ERPProductSyncRequest.model_validate(
        {
            "meta": {"source_system": "ERP", "dry_run": True},
            "items": [{"sku": "ERP-001", "name": "ERP Product 1"}],
        }
    )

    result = service.sync_products(payload)
    assert result.success is True
    assert result.processed == 1
    assert result.dry_run is True


def test_sync_products_create_and_update(db):
    service = IntegrationService(db)
    create_payload = ERPProductSyncRequest.model_validate(
        {
            "meta": {"source_system": "ERP"},
            "items": [{"sku": "ERP-002", "name": "Created Name", "category_name": "ERP Cat"}],
        }
    )
    create_result = service.sync_products(create_payload)
    assert create_result.created == 1
    assert create_result.updated == 0

    update_payload = ERPProductSyncRequest.model_validate(
        {
            "meta": {"source_system": "ERP"},
            "items": [{"sku": "ERP-002", "name": "Updated Name", "product_family": "Audio"}],
        }
    )
    update_result = service.sync_products(update_payload)
    assert update_result.created == 0
    assert update_result.updated == 1


def test_sync_inventory_updates_existing_and_skips_unknown_sku(db):
    service = IntegrationService(db)
    product = _seed_product(db)
    inventory = Inventory(
        product_id=product.id,
        location="Warehouse A",
        on_hand_qty=100,
        allocated_qty=10,
        in_transit_qty=5,
        safety_stock=20,
        reorder_point=30,
        status="normal",
    )
    db.add(inventory)
    db.commit()

    payload = ERPInventorySyncRequest.model_validate(
        {
            "meta": {"source_system": "ERP"},
            "items": [
                {
                    "sku": product.sku,
                    "location": inventory.location,
                    "on_hand_qty": "321.00",
                    "allocated_qty": "20.00",
                    "in_transit_qty": "10.00",
                },
                {
                    "sku": "UNKNOWN-SKU",
                    "location": "Warehouse X",
                    "on_hand_qty": "1.00",
                },
            ],
        }
    )

    result = service.sync_inventory(payload)
    assert result.updated == 1
    assert result.skipped == 1


def test_sync_demand_actuals_updates_matching_plan_and_skips_missing(db):
    service = IntegrationService(db)
    product = _seed_product(db, sku="SKU-ERP-2")
    demand_plan = DemandPlan(
        product_id=product.id,
        period=date(2026, 3, 1),
        region="Global",
        channel="All",
        forecast_qty=500,
        status="draft",
        version=1,
    )
    db.add(demand_plan)
    db.commit()

    payload = ERPDemandActualSyncRequest.model_validate(
        {
            "meta": {"source_system": "ERP"},
            "items": [
                {
                    "sku": product.sku,
                    "period": str(demand_plan.period),
                    "actual_qty": "777.00",
                    "region": demand_plan.region,
                    "channel": demand_plan.channel,
                },
                {
                    "sku": product.sku,
                    "period": str(date(2099, 1, 1)),
                    "actual_qty": "1.00",
                    "region": "Global",
                    "channel": "All",
                },
            ],
        }
    )

    result = service.sync_demand_actuals(payload)
    assert result.updated == 1
    assert result.skipped == 1


def test_publish_plan_requires_approved_status(db):
    service = IntegrationService(db)
    product = _seed_product(db, sku="SKU-ERP-3")
    demand_plan = DemandPlan(
        product_id=product.id,
        period=date(2026, 4, 1),
        region="Global",
        channel="All",
        forecast_qty=100,
        status="draft",
        version=1,
    )
    supply_plan = SupplyPlan(
        product_id=product.id,
        period=date(2026, 4, 1),
        location="Main",
        planned_prod_qty=100,
        status="draft",
        version=1,
    )
    db.add(demand_plan)
    db.add(supply_plan)
    db.commit()

    demand_result = service.publish_demand_plan(demand_plan.id)
    supply_result = service.publish_supply_plan(supply_plan.id)

    assert demand_result.success is False
    assert "not approved" in demand_result.message
    assert supply_result.success is False
    assert "not approved" in supply_result.message
