"""
KPI Router — Thin Controller (SRP / DIP)
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date
from math import ceil

from app.database import get_db
from app.models.user import User
from app.schemas.kpi import KPIMetricCreate, KPIMetricResponse, KPIMetricListResponse, KPIDashboardData, KPITargetRequest
from app.dependencies import get_current_user, require_roles
from app.services.kpi_service import KPIService

router = APIRouter(prefix="/kpi", tags=["KPI & Analytics"])

ADMIN_ROLES = ["admin", "executive"]


def get_kpi_service(db: Session = Depends(get_db)) -> KPIService:
    return KPIService(db)


@router.get("/metrics", response_model=KPIMetricListResponse)
def list_kpi_metrics(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    period_from: Optional[date] = None,
    period_to: Optional[date] = None,
    service: KPIService = Depends(get_kpi_service),
    _: User = Depends(get_current_user),
):
    # NOTE: We return a paginated contract (items/total/page/page_size/total_pages)
    # to match the frontend's PaginatedResponse<T> pattern.
    items_all = service.list_metrics(category=category, period_from=period_from, period_to=period_to)
    total = len(items_all)
    start = (page - 1) * page_size
    end = start + page_size
    items = items_all[start:end]
    return KPIMetricListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total else 0,
    )


@router.post("/metrics", response_model=KPIMetricResponse, status_code=201)
def create_kpi_metric(
    data: KPIMetricCreate,
    service: KPIService = Depends(get_kpi_service),
    current_user: User = Depends(require_roles(ADMIN_ROLES)),
):
    return service.create_metric(data, user_id=current_user.id)


@router.get("/metrics/{metric_id}", response_model=KPIMetricResponse)
def get_kpi_metric(
    metric_id: int,
    service: KPIService = Depends(get_kpi_service),
    _: User = Depends(get_current_user),
):
    return service.get_metric(metric_id)


@router.get("/dashboard", response_model=KPIDashboardData)
def kpi_dashboard(
    service: KPIService = Depends(get_kpi_service),
    _: User = Depends(get_current_user),
):
    return service.get_dashboard()


@router.get("/alerts")
def kpi_alerts(
    service: KPIService = Depends(get_kpi_service),
    _: User = Depends(get_current_user),
):
    return service.get_alerts()


@router.post("/targets", response_model=KPIMetricResponse)
def set_kpi_target(
    body: KPITargetRequest,
    service: KPIService = Depends(get_kpi_service),
    current_user: User = Depends(require_roles(ADMIN_ROLES)),
):
    return service.set_target(body, user_id=current_user.id)
