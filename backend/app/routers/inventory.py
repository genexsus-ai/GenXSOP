"""
Inventory Router — Thin Controller (SRP / DIP)
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from decimal import Decimal

from app.database import get_db
from app.models.user import User
from app.schemas.inventory import (
    InventoryUpdate,
    InventoryResponse,
    InventoryListResponse,
    InventoryHealthSummary,
    InventoryOptimizationRunRequest,
    InventoryOptimizationRunResponse,
    InventoryPolicyOverride,
    InventoryExceptionView,
    InventoryExceptionUpdateRequest,
    InventoryRecommendationGenerateRequest,
    InventoryPolicyRecommendationView,
    InventoryRecommendationDecisionRequest,
    InventoryRebalanceRecommendationView,
    InventoryAutoApplyRequest,
    InventoryAutoApplyResponse,
    InventoryControlTowerSummary,
)
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


@router.post("/optimization/runs", response_model=InventoryOptimizationRunResponse)
def run_inventory_optimization(
    payload: InventoryOptimizationRunRequest,
    service: InventoryService = Depends(get_inventory_service),
    current_user: User = Depends(require_roles(MANAGER_ROLES)),
):
    return service.run_optimization(payload, user_id=current_user.id)


@router.get("/exceptions", response_model=list[InventoryExceptionView])
def get_inventory_policy_exceptions(
    product_id: Optional[int] = None,
    location: Optional[str] = None,
    status: Optional[str] = None,
    owner_user_id: Optional[int] = None,
    service: InventoryService = Depends(get_inventory_service),
    _: User = Depends(get_current_user),
):
    return service.get_policy_exceptions(
        product_id=product_id,
        location=location,
        status=status,
        owner_user_id=owner_user_id,
    )


@router.patch("/exceptions/{exception_id}", response_model=InventoryExceptionView)
def update_inventory_policy_exception(
    exception_id: int,
    payload: InventoryExceptionUpdateRequest,
    service: InventoryService = Depends(get_inventory_service),
    current_user: User = Depends(require_roles(MANAGER_ROLES)),
):
    return service.update_exception(exception_id, payload, user_id=current_user.id)


@router.post("/recommendations/generate", response_model=list[InventoryPolicyRecommendationView])
def generate_inventory_policy_recommendations(
    payload: InventoryRecommendationGenerateRequest,
    service: InventoryService = Depends(get_inventory_service),
    current_user: User = Depends(require_roles(MANAGER_ROLES)),
):
    return service.generate_recommendations(payload, user_id=current_user.id)


@router.get("/recommendations", response_model=list[InventoryPolicyRecommendationView])
def list_inventory_policy_recommendations(
    status: Optional[str] = None,
    inventory_id: Optional[int] = None,
    product_id: Optional[int] = None,
    location: Optional[str] = None,
    service: InventoryService = Depends(get_inventory_service),
    _: User = Depends(get_current_user),
):
    return service.list_recommendations(
        status=status,
        inventory_id=inventory_id,
        product_id=product_id,
        location=location,
    )


@router.post("/recommendations/{recommendation_id}/decision", response_model=InventoryPolicyRecommendationView)
def decide_inventory_policy_recommendation(
    recommendation_id: int,
    payload: InventoryRecommendationDecisionRequest,
    service: InventoryService = Depends(get_inventory_service),
    current_user: User = Depends(require_roles(MANAGER_ROLES)),
):
    return service.decide_recommendation(recommendation_id, payload, user_id=current_user.id)


@router.get("/rebalance/recommendations", response_model=list[InventoryRebalanceRecommendationView])
def get_inventory_rebalance_recommendations(
    product_id: Optional[int] = None,
    min_transfer_qty: float = Query(1.0, ge=0),
    service: InventoryService = Depends(get_inventory_service),
    _: User = Depends(get_current_user),
):
    return service.get_rebalance_recommendations(
        product_id=product_id,
        min_transfer_qty=Decimal(str(min_transfer_qty)),
    )


@router.post("/recommendations/auto-apply", response_model=InventoryAutoApplyResponse)
def auto_apply_inventory_recommendations(
    payload: InventoryAutoApplyRequest,
    service: InventoryService = Depends(get_inventory_service),
    current_user: User = Depends(require_roles(MANAGER_ROLES)),
):
    return service.auto_apply_recommendations(payload, user_id=current_user.id)


@router.get("/control-tower/summary", response_model=InventoryControlTowerSummary)
def get_inventory_control_tower_summary(
    service: InventoryService = Depends(get_inventory_service),
    _: User = Depends(get_current_user),
):
    return service.get_control_tower_summary()


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


@router.put("/policies/{inventory_id}/override", response_model=InventoryResponse)
def override_inventory_policy(
    inventory_id: int,
    payload: InventoryPolicyOverride,
    service: InventoryService = Depends(get_inventory_service),
    current_user: User = Depends(require_roles(MANAGER_ROLES)),
):
    return service.apply_policy_override(inventory_id, payload, user_id=current_user.id)
