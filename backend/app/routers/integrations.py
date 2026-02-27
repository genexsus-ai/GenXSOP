from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.dependencies import require_roles
from app.schemas.integration import (
    ERPProductSyncRequest,
    ERPInventorySyncRequest,
    ERPDemandActualSyncRequest,
    IntegrationOperationResponse,
)
from app.services.integration_service import IntegrationService


router = APIRouter(prefix="/integrations", tags=["ERP/WMS Integration"])

INTEGRATION_ROLES = ["admin", "sop_coordinator"]


def get_integration_service(db: Session = Depends(get_db)) -> IntegrationService:
    return IntegrationService(db)


@router.post("/erp/products/sync", response_model=IntegrationOperationResponse)
def sync_erp_products(
    payload: ERPProductSyncRequest,
    service: IntegrationService = Depends(get_integration_service),
    _: User = Depends(require_roles(INTEGRATION_ROLES)),
):
    return service.sync_products(payload)


@router.post("/erp/inventory/sync", response_model=IntegrationOperationResponse)
def sync_erp_inventory(
    payload: ERPInventorySyncRequest,
    service: IntegrationService = Depends(get_integration_service),
    _: User = Depends(require_roles(INTEGRATION_ROLES)),
):
    return service.sync_inventory(payload)


@router.post("/erp/demand-actuals/sync", response_model=IntegrationOperationResponse)
def sync_erp_demand_actuals(
    payload: ERPDemandActualSyncRequest,
    service: IntegrationService = Depends(get_integration_service),
    _: User = Depends(require_roles(INTEGRATION_ROLES)),
):
    return service.sync_demand_actuals(payload)


@router.post("/erp/publish/demand-plan/{plan_id}", response_model=IntegrationOperationResponse)
def publish_demand_plan_to_erp(
    plan_id: int,
    service: IntegrationService = Depends(get_integration_service),
    _: User = Depends(require_roles(INTEGRATION_ROLES)),
):
    return service.publish_demand_plan(plan_id)


@router.post("/erp/publish/supply-plan/{plan_id}", response_model=IntegrationOperationResponse)
def publish_supply_plan_to_erp(
    plan_id: int,
    service: IntegrationService = Depends(get_integration_service),
    _: User = Depends(require_roles(INTEGRATION_ROLES)),
):
    return service.publish_supply_plan(plan_id)
