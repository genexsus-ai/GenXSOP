"""
Demand Planning Router — Thin Controller (SRP)

Principles applied:
- Single Responsibility Principle (SRP): Router only handles HTTP concerns (routing, auth, serialization).
- Dependency Inversion Principle (DIP): Depends on DemandService abstraction, not DB directly.
- All business logic delegated to DemandService.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from app.database import get_db
from app.models.user import User
from app.schemas.demand import (
    DemandPlanCreate, DemandPlanUpdate, DemandPlanResponse,
    DemandPlanListResponse, AdjustmentRequest, ApprovalRequest,
)
from app.dependencies import get_current_user, require_roles
from app.services.demand_service import DemandService

router = APIRouter(prefix="/demand", tags=["Demand Planning"])

PLANNER_ROLES = ["admin", "demand_planner", "supply_planner", "sop_coordinator"]
APPROVER_ROLES = ["admin", "executive"]


def get_demand_service(db: Session = Depends(get_db)) -> DemandService:
    """FastAPI dependency that provides a DemandService instance."""
    return DemandService(db)


@router.get("/plans", response_model=DemandPlanListResponse)
def list_demand_plans(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    product_id: Optional[int] = None,
    region: Optional[str] = None,
    channel: Optional[str] = None,
    status: Optional[str] = None,
    period_from: Optional[date] = None,
    period_to: Optional[date] = None,
    service: DemandService = Depends(get_demand_service),
    _: User = Depends(get_current_user),
):
    return service.list_plans(
        page=page, page_size=page_size, product_id=product_id,
        region=region, channel=channel, status=status,
        period_from=period_from, period_to=period_to,
    )


@router.post("/plans", response_model=DemandPlanResponse, status_code=201)
def create_demand_plan(
    data: DemandPlanCreate,
    service: DemandService = Depends(get_demand_service),
    current_user: User = Depends(require_roles(PLANNER_ROLES)),
):
    return service.create_plan(data, created_by=current_user.id)


@router.get("/plans/{plan_id}", response_model=DemandPlanResponse)
def get_demand_plan(
    plan_id: int,
    service: DemandService = Depends(get_demand_service),
    _: User = Depends(get_current_user),
):
    return service.get_plan(plan_id)


@router.put("/plans/{plan_id}", response_model=DemandPlanResponse)
def update_demand_plan(
    plan_id: int,
    data: DemandPlanUpdate,
    service: DemandService = Depends(get_demand_service),
    current_user: User = Depends(require_roles(PLANNER_ROLES)),
):
    return service.update_plan(plan_id, data, user_id=current_user.id)


@router.post("/plans/{plan_id}/adjust", response_model=DemandPlanResponse)
def adjust_forecast(
    plan_id: int,
    body: AdjustmentRequest,
    service: DemandService = Depends(get_demand_service),
    current_user: User = Depends(require_roles(PLANNER_ROLES)),
):
    return service.adjust_forecast(plan_id, body, user_id=current_user.id)


@router.post("/plans/{plan_id}/submit", response_model=DemandPlanResponse)
def submit_demand_plan(
    plan_id: int,
    service: DemandService = Depends(get_demand_service),
    current_user: User = Depends(require_roles(PLANNER_ROLES)),
):
    return service.submit_plan(plan_id, user_id=current_user.id)


@router.post("/plans/{plan_id}/approve", response_model=DemandPlanResponse)
def approve_demand_plan(
    plan_id: int,
    body: ApprovalRequest,
    service: DemandService = Depends(get_demand_service),
    current_user: User = Depends(require_roles(APPROVER_ROLES)),
):
    return service.approve_plan(plan_id, body, approver_id=current_user.id)


@router.post("/plans/{plan_id}/reject", response_model=DemandPlanResponse)
def reject_demand_plan(
    plan_id: int,
    body: ApprovalRequest,
    service: DemandService = Depends(get_demand_service),
    current_user: User = Depends(require_roles(APPROVER_ROLES)),
):
    return service.reject_plan(plan_id, body, approver_id=current_user.id)


@router.delete("/plans/{plan_id}")
def delete_demand_plan(
    plan_id: int,
    service: DemandService = Depends(get_demand_service),
    current_user: User = Depends(require_roles(PLANNER_ROLES)),
):
    service.delete_plan(plan_id, user_id=current_user.id)
    return {"message": "Demand plan deleted successfully"}
