from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.user import User
from app.schemas.agentic_scheduling_config import (
    AgenticSchedulingConfigResponse,
    AgenticSchedulingConfigUpsertRequest,
)
from app.services.agentic_scheduling_config_service import AgenticSchedulingConfigService


router = APIRouter(prefix="/config", tags=["Agentic Scheduling Config"])

ADMIN_ROLES = ["admin", "supply_planner", "sop_coordinator"]


def get_config_service(db: Session = Depends(get_db)) -> AgenticSchedulingConfigService:
    return AgenticSchedulingConfigService(db)


@router.get("/objectives", response_model=AgenticSchedulingConfigResponse)
def get_objectives(
    scope: str = Query("global"),
    name: str = Query("default"),
    service: AgenticSchedulingConfigService = Depends(get_config_service),
    _: User = Depends(get_current_user),
):
    return service.get_objectives(scope=scope, name=name)


@router.put("/objectives", response_model=AgenticSchedulingConfigResponse)
def upsert_objectives(
    payload: AgenticSchedulingConfigUpsertRequest,
    service: AgenticSchedulingConfigService = Depends(get_config_service),
    current_user: User = Depends(require_roles(ADMIN_ROLES)),
):
    return service.upsert_objectives(payload=payload, user_id=current_user.id)


@router.get("/policies", response_model=AgenticSchedulingConfigResponse)
def get_policies(
    scope: str = Query("global"),
    name: str = Query("default"),
    service: AgenticSchedulingConfigService = Depends(get_config_service),
    _: User = Depends(get_current_user),
):
    return service.get_policies(scope=scope, name=name)


@router.put("/policies", response_model=AgenticSchedulingConfigResponse)
def upsert_policies(
    payload: AgenticSchedulingConfigUpsertRequest,
    service: AgenticSchedulingConfigService = Depends(get_config_service),
    current_user: User = Depends(require_roles(ADMIN_ROLES)),
):
    return service.upsert_policies(payload=payload, user_id=current_user.id)
