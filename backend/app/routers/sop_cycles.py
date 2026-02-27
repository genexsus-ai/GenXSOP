"""
S&OP Cycle Router — Thin Controller (SRP / DIP)
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.sop_cycle import SOPCycleCreate, SOPCycleUpdate, SOPCycleResponse, SOPCycleListResponse
from app.dependencies import get_current_user, require_roles
from app.services.sop_cycle_service import SOPCycleService

router = APIRouter(prefix="/sop-cycles", tags=["S&OP Cycle"])

COORDINATOR_ROLES = ["admin", "sop_coordinator"]
EXECUTIVE_ROLES = ["admin", "executive"]


def get_sop_service(db: Session = Depends(get_db)) -> SOPCycleService:
    return SOPCycleService(db)


@router.get("", response_model=SOPCycleListResponse)
def list_sop_cycles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: SOPCycleService = Depends(get_sop_service),
    _: User = Depends(get_current_user),
):
    return service.list_cycles(page=page, page_size=page_size)


@router.post("", response_model=SOPCycleResponse, status_code=201)
def create_sop_cycle(
    data: SOPCycleCreate,
    service: SOPCycleService = Depends(get_sop_service),
    current_user: User = Depends(require_roles(COORDINATOR_ROLES)),
):
    return service.create_cycle(data, created_by=current_user.id)


@router.get("/active")
def get_active_cycle(
    service: SOPCycleService = Depends(get_sop_service),
    _: User = Depends(get_current_user),
):
    cycle = service.get_active_cycle()
    if not cycle:
        return {"active": False, "message": "No active S&OP cycle"}
    return cycle


@router.get("/{cycle_id}", response_model=SOPCycleResponse)
def get_sop_cycle(
    cycle_id: int,
    service: SOPCycleService = Depends(get_sop_service),
    _: User = Depends(get_current_user),
):
    return service.get_cycle(cycle_id)


@router.put("/{cycle_id}", response_model=SOPCycleResponse)
def update_sop_cycle(
    cycle_id: int,
    data: SOPCycleUpdate,
    service: SOPCycleService = Depends(get_sop_service),
    current_user: User = Depends(require_roles(COORDINATOR_ROLES)),
):
    return service.update_cycle(cycle_id, data, user_id=current_user.id)


@router.post("/{cycle_id}/advance", response_model=SOPCycleResponse)
def advance_sop_cycle(
    cycle_id: int,
    service: SOPCycleService = Depends(get_sop_service),
    current_user: User = Depends(require_roles(COORDINATOR_ROLES)),
):
    return service.advance_step(cycle_id, user_id=current_user.id)


@router.post("/{cycle_id}/complete", response_model=SOPCycleResponse)
def complete_sop_cycle(
    cycle_id: int,
    service: SOPCycleService = Depends(get_sop_service),
    current_user: User = Depends(require_roles(EXECUTIVE_ROLES)),
):
    return service.complete_cycle(cycle_id, user_id=current_user.id)
