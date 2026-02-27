"""
Inventory Router — Thin Controller (SRP / DIP)
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.schemas.inventory import InventoryUpdate, InventoryResponse, InventoryListResponse, InventoryHealthSummary
from app.dependencies import get_current_user, require_roles
from app.services.inventory_service import InventoryService

router = APIRouter(prefix="/inventory", tags=["Inventory Management"])

MANAGER_ROLES = ["admin", "inventory_manager", "supply_planner"]


def get_inventory_service(db: Session = Depends(get_db)) -> InventoryService:
    return InventoryService(db)


@router.get("", response_model=InventoryListResponse)
def list_inventory(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    product_id: Optional[int] = None,
    location: Optional[str] = None,
    status: Optional[str] = None,
    service: InventoryService = Depends(get_inventory_service),
    _: User = Depends(get_current_user),
):
    return service.list_inventory(
        page=page, page_size=page_size,
        product_id=product_id, location=location, status=status,
    )


@router.get("/health", response_model=InventoryHealthSummary)
def inventory_health(
    service: InventoryService = Depends(get_inventory_service),
    _: User = Depends(get_current_user),
):
    return service.get_health_summary()


@router.get("/alerts")
def inventory_alerts(
    service: InventoryService = Depends(get_inventory_service),
    _: User = Depends(get_current_user),
):
    return service.get_alerts()


@router.get("/{inventory_id}", response_model=InventoryResponse)
def get_inventory(
    inventory_id: int,
    service: InventoryService = Depends(get_inventory_service),
    _: User = Depends(get_current_user),
):
    return service.get_inventory(inventory_id)


@router.put("/{inventory_id}", response_model=InventoryResponse)
def update_inventory(
    inventory_id: int,
    data: InventoryUpdate,
    service: InventoryService = Depends(get_inventory_service),
    current_user: User = Depends(require_roles(MANAGER_ROLES)),
):
    return service.update_inventory(inventory_id, data, user_id=current_user.id)
