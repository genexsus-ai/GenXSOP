"""
Scenarios Router — Thin Controller (SRP / DIP)
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.user import User
from app.schemas.scenario import ScenarioCreate, ScenarioUpdate, ScenarioResponse, ScenarioListResponse
from app.dependencies import get_current_user, require_roles
from app.services.scenario_service import ScenarioService

router = APIRouter(prefix="/scenarios", tags=["Scenario Planning"])

PLANNER_ROLES = ["admin", "demand_planner", "supply_planner", "finance_analyst", "sop_coordinator"]
APPROVER_ROLES = ["admin", "executive"]


def get_scenario_service(db: Session = Depends(get_db)) -> ScenarioService:
    return ScenarioService(db)


@router.get("", response_model=ScenarioListResponse)
def list_scenarios(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: ScenarioService = Depends(get_scenario_service),
    _: User = Depends(get_current_user),
):
    return service.list_scenarios(page=page, page_size=page_size)


@router.post("", response_model=ScenarioResponse, status_code=201)
def create_scenario(
    data: ScenarioCreate,
    service: ScenarioService = Depends(get_scenario_service),
    current_user: User = Depends(require_roles(PLANNER_ROLES)),
):
    return service.create_scenario(data, created_by=current_user.id)


@router.get("/{scenario_id}", response_model=ScenarioResponse)
def get_scenario(
    scenario_id: int,
    service: ScenarioService = Depends(get_scenario_service),
    _: User = Depends(get_current_user),
):
    return service.get_scenario(scenario_id)


@router.put("/{scenario_id}", response_model=ScenarioResponse)
def update_scenario(
    scenario_id: int,
    data: ScenarioUpdate,
    service: ScenarioService = Depends(get_scenario_service),
    current_user: User = Depends(require_roles(PLANNER_ROLES)),
):
    return service.update_scenario(scenario_id, data, user_id=current_user.id)


@router.delete("/{scenario_id}")
def delete_scenario(
    scenario_id: int,
    service: ScenarioService = Depends(get_scenario_service),
    current_user: User = Depends(require_roles(PLANNER_ROLES)),
):
    service.delete_scenario(scenario_id, user_id=current_user.id)
    return {"message": "Scenario deleted successfully"}


@router.post("/{scenario_id}/run", response_model=ScenarioResponse)
def run_scenario(
    scenario_id: int,
    service: ScenarioService = Depends(get_scenario_service),
    current_user: User = Depends(require_roles(PLANNER_ROLES)),
):
    return service.run_scenario(scenario_id, user_id=current_user.id)


@router.post("/{scenario_id}/submit", response_model=ScenarioResponse)
def submit_scenario(
    scenario_id: int,
    service: ScenarioService = Depends(get_scenario_service),
    current_user: User = Depends(require_roles(PLANNER_ROLES)),
):
    return service.submit_scenario(scenario_id, user_id=current_user.id)


@router.post("/{scenario_id}/approve", response_model=ScenarioResponse)
def approve_scenario(
    scenario_id: int,
    service: ScenarioService = Depends(get_scenario_service),
    current_user: User = Depends(require_roles(APPROVER_ROLES)),
):
    return service.approve_scenario(scenario_id, approver_id=current_user.id)


@router.post("/{scenario_id}/reject", response_model=ScenarioResponse)
def reject_scenario(
    scenario_id: int,
    service: ScenarioService = Depends(get_scenario_service),
    current_user: User = Depends(require_roles(APPROVER_ROLES)),
):
    return service.reject_scenario(scenario_id, approver_id=current_user.id)


@router.post("/compare")
def compare_scenarios(
    ids: List[int],
    service: ScenarioService = Depends(get_scenario_service),
    _: User = Depends(get_current_user),
):
    return service.compare_scenarios(ids)


@router.get("/{scenario_id}/tradeoff-summary")
def get_tradeoff_summary(
    scenario_id: int,
    service: ScenarioService = Depends(get_scenario_service),
    _: User = Depends(get_current_user),
):
    return service.get_tradeoff_summary(scenario_id)
