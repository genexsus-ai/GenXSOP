"""
Supply Planning Router — Thin Controller (SRP / DIP)
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date

from app.database import get_db
from app.models.user import User
from app.schemas.supply import (
    SupplyPlanCreate, SupplyPlanUpdate, SupplyPlanResponse,
    SupplyPlanListResponse, GapAnalysisItem,
)
from app.dependencies import get_current_user, require_roles
from app.services.supply_service import SupplyService

router = APIRouter(prefix="/supply", tags=["Supply Planning"])

PLANNER_ROLES = ["admin", "supply_planner", "sop_coordinator"]
APPROVER_ROLES = ["admin", "executive"]


def get_supply_service(db: Session = Depends(get_db)) -> SupplyService:
    return SupplyService(db)


@router.get("/plans", response_model=SupplyPlanListResponse)
def list_supply_plans(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    product_id: Optional[int] = None,
    location: Optional[str] = None,
    status: Optional[str] = None,
    period_from: Optional[date] = None,
    period_to: Optional[date] = None,
    service: SupplyService = Depends(get_supply_service),
    _: User = Depends(get_current_user),
):
    return service.list_plans(
        page=page, page_size=page_size, product_id=product_id,
        location=location, status=status, period_from=period_from, period_to=period_to,
    )


@router.post("/plans", response_model=SupplyPlanResponse, status_code=201)
def create_supply_plan(
    data: SupplyPlanCreate,
    service: SupplyService = Depends(get_supply_service),
    current_user: User = Depends(require_roles(PLANNER_ROLES)),
):
    return service.create_plan(data, created_by=current_user.id)


@router.get("/plans/{plan_id}", response_model=SupplyPlanResponse)
def get_supply_plan(
    plan_id: int,
    service: SupplyService = Depends(get_supply_service),
    _: User = Depends(get_current_user),
):
    return service.get_plan(plan_id)


@router.put("/plans/{plan_id}", response_model=SupplyPlanResponse)
def update_supply_plan(
    plan_id: int,
    data: SupplyPlanUpdate,
    service: SupplyService = Depends(get_supply_service),
    current_user: User = Depends(require_roles(PLANNER_ROLES)),
):
    return service.update_plan(plan_id, data, user_id=current_user.id)


@router.post("/plans/{plan_id}/submit", response_model=SupplyPlanResponse)
def submit_supply_plan(
    plan_id: int,
    service: SupplyService = Depends(get_supply_service),
    current_user: User = Depends(require_roles(PLANNER_ROLES)),
):
    return service.submit_plan(plan_id, user_id=current_user.id)


@router.post("/plans/{plan_id}/approve", response_model=SupplyPlanResponse)
def approve_supply_plan(
    plan_id: int,
    service: SupplyService = Depends(get_supply_service),
    current_user: User = Depends(require_roles(APPROVER_ROLES)),
):
    return service.approve_plan(plan_id, user_id=current_user.id)


@router.delete("/plans/{plan_id}")
def delete_supply_plan(
    plan_id: int,
    service: SupplyService = Depends(get_supply_service),
    current_user: User = Depends(require_roles(PLANNER_ROLES)),
):
    service.delete_plan(plan_id, user_id=current_user.id)
    return {"message": "Supply plan deleted successfully"}


@router.get("/gap-analysis", response_model=List[GapAnalysisItem])
def gap_analysis(
    period: Optional[date] = None,
    service: SupplyService = Depends(get_supply_service),
    _: User = Depends(get_current_user),
):
    return service.gap_analysis(period=period)
