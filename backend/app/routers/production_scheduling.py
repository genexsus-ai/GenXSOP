from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.user import User
from app.schemas.production_schedule import (
    ProductionCapacitySummaryResponse,
    ProductionScheduleGenerateRequest,
    ProductionScheduleResequenceRequest,
    ProductionScheduleResponse,
    ProductionScheduleStatusUpdateRequest,
)
from app.services.production_schedule_service import ProductionScheduleService


router = APIRouter(prefix="/production-scheduling", tags=["Production Scheduling"])

PLANNER_ROLES = ["admin", "supply_planner", "sop_coordinator"]
EXECUTION_ROLES = ["admin", "supply_planner", "sop_coordinator", "executive"]


def get_schedule_service(db: Session = Depends(get_db)) -> ProductionScheduleService:
    return ProductionScheduleService(db)


@router.get("/schedules", response_model=List[ProductionScheduleResponse])
def list_schedules(
    product_id: Optional[int] = None,
    period: Optional[date] = None,
    supply_plan_id: Optional[int] = None,
    workcenter: Optional[str] = None,
    line: Optional[str] = None,
    shift: Optional[str] = None,
    status: Optional[str] = None,
    service: ProductionScheduleService = Depends(get_schedule_service),
    _: User = Depends(get_current_user),
):
    return service.list_schedules(
        product_id=product_id,
        period=period,
        supply_plan_id=supply_plan_id,
        workcenter=workcenter,
        line=line,
        shift=shift,
        status=status,
    )


@router.post("/generate", response_model=List[ProductionScheduleResponse], status_code=201)
def generate_schedule(
    body: ProductionScheduleGenerateRequest,
    service: ProductionScheduleService = Depends(get_schedule_service),
    current_user: User = Depends(require_roles(PLANNER_ROLES)),
):
    return service.generate_schedule(body=body, user_id=current_user.id)


@router.patch("/schedules/{schedule_id}/status", response_model=ProductionScheduleResponse)
def update_schedule_status(
    schedule_id: int,
    body: ProductionScheduleStatusUpdateRequest,
    service: ProductionScheduleService = Depends(get_schedule_service),
    _: User = Depends(require_roles(EXECUTION_ROLES)),
):
    return service.update_schedule_status(schedule_id=schedule_id, body=body)


@router.get("/capacity-summary", response_model=ProductionCapacitySummaryResponse)
def capacity_summary(
    supply_plan_id: int,
    service: ProductionScheduleService = Depends(get_schedule_service),
    _: User = Depends(get_current_user),
):
    return service.summarize_capacity(supply_plan_id=supply_plan_id)


@router.post("/schedules/{schedule_id}/resequence", response_model=List[ProductionScheduleResponse])
def resequence_schedule(
    schedule_id: int,
    body: ProductionScheduleResequenceRequest,
    service: ProductionScheduleService = Depends(get_schedule_service),
    _: User = Depends(require_roles(PLANNER_ROLES)),
):
    return service.resequence_schedule(schedule_id=schedule_id, body=body)
