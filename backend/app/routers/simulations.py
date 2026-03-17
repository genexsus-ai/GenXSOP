from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.user import User
from app.schemas.simulation import SimulationRunCreateRequest, SimulationRunResponse
from app.services.simulation_service import SimulationService


router = APIRouter(prefix="/simulations", tags=["Simulations"])

PLANNER_ROLES = ["admin", "supply_planner", "sop_coordinator"]


def get_simulation_service(db: Session = Depends(get_db)) -> SimulationService:
    return SimulationService(db)


@router.post("", response_model=SimulationRunResponse)
def run_simulation(
    body: SimulationRunCreateRequest,
    service: SimulationService = Depends(get_simulation_service),
    current_user: User = Depends(require_roles(PLANNER_ROLES)),
):
    return service.run_simulation(body, user_id=current_user.id)


@router.get("/{simulation_id}", response_model=SimulationRunResponse)
def get_simulation(
    simulation_id: str,
    service: SimulationService = Depends(get_simulation_service),
    _: User = Depends(get_current_user),
):
    return service.get_simulation(simulation_id)


@router.get("", response_model=list[SimulationRunResponse])
def list_simulations(
    recommendation_id: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    scenario_name: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    service: SimulationService = Depends(get_simulation_service),
    _: User = Depends(get_current_user),
):
    return service.list_simulations(
        recommendation_id=recommendation_id,
        status=status,
        scenario_name=scenario_name,
        limit=limit,
    )
