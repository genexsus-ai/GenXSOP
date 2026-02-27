"""
Inventory Service — Service Layer (SRP / DIP)
"""
from math import ceil
from typing import Optional
from decimal import Decimal
from sqlalchemy.orm import Session

from app.repositories.inventory_repository import InventoryRepository
from app.models.inventory import Inventory
from app.schemas.inventory import InventoryUpdate, InventoryListResponse, InventoryHealthSummary
from app.core.exceptions import EntityNotFoundException, to_http_exception
from app.utils.events import get_event_bus, EntityUpdatedEvent


class InventoryService:

    def __init__(self, db: Session):
        self._repo = InventoryRepository(db)
        self._bus = get_event_bus()

    def list_inventory(self, page: int = 1, page_size: int = 20, **filters) -> InventoryListResponse:
        items, total = self._repo.list_paginated(page=page, page_size=page_size, **filters)
        return InventoryListResponse(
            items=items, total=total, page=page, page_size=page_size,
            total_pages=ceil(total / page_size) if total else 0,
        )

    def get_inventory(self, inventory_id: int) -> Inventory:
        inv = self._repo.get_by_id(inventory_id)
        if not inv:
            raise to_http_exception(EntityNotFoundException("Inventory", inventory_id))
        return inv

    def update_inventory(self, inventory_id: int, data: InventoryUpdate, user_id: int) -> Inventory:
        inv = self.get_inventory(inventory_id)
        updates = data.model_dump(exclude_unset=True)
        result = self._repo.update(inv, updates)
        # Recalculate status based on new quantities
        result = self._recalculate_status(result)
        self._bus.publish(EntityUpdatedEvent(
            entity_type="inventory", entity_id=inventory_id, user_id=user_id, new_values=updates,
        ))
        return result

    def get_health_summary(self) -> InventoryHealthSummary:
        all_inv = self._repo.get_all_inventory()
        total = len(all_inv)
        if total == 0:
            return InventoryHealthSummary(
                total_products=0, normal_count=0, low_count=0, critical_count=0, excess_count=0,
                total_value=Decimal("0"), normal_pct=0.0, low_pct=0.0, critical_pct=0.0, excess_pct=0.0,
            )
        counts = {"normal": 0, "low": 0, "critical": 0, "excess": 0}
        total_value = Decimal("0")
        for inv in all_inv:
            counts[inv.status] = counts.get(inv.status, 0) + 1
            total_value += inv.valuation or Decimal("0")
        return InventoryHealthSummary(
            total_products=total,
            normal_count=counts["normal"],
            low_count=counts["low"],
            critical_count=counts["critical"],
            excess_count=counts["excess"],
            total_value=total_value,
            normal_pct=round(counts["normal"] / total * 100, 1),
            low_pct=round(counts["low"] / total * 100, 1),
            critical_pct=round(counts["critical"] / total * 100, 1),
            excess_pct=round(counts["excess"] / total * 100, 1),
        )

    def get_alerts(self) -> dict:
        return {
            "critical": [
                {"id": i.id, "product_id": i.product_id, "location": i.location, "on_hand_qty": float(i.on_hand_qty)}
                for i in self._repo.get_critical()
            ],
            "low": [
                {"id": i.id, "product_id": i.product_id, "location": i.location, "on_hand_qty": float(i.on_hand_qty)}
                for i in self._repo.get_low()
            ],
            "excess": [
                {"id": i.id, "product_id": i.product_id, "location": i.location, "on_hand_qty": float(i.on_hand_qty)}
                for i in self._repo.get_excess()
            ],
        }

    def _recalculate_status(self, inv: Inventory) -> Inventory:
        """Business rule: recalculate inventory status based on thresholds."""
        on_hand = inv.on_hand_qty or Decimal("0")
        safety = inv.safety_stock or Decimal("0")
        reorder = inv.reorder_point or Decimal("0")
        max_stock = inv.max_stock
        if on_hand < reorder:
            new_status = "critical"
        elif on_hand < safety:
            new_status = "low"
        elif max_stock and on_hand > max_stock:
            new_status = "excess"
        else:
            new_status = "normal"
        return self._repo.update(inv, {"status": new_status})
