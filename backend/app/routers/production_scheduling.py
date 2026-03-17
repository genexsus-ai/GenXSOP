import asyncio
import json
from datetime import date
from typing import AsyncGenerator, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.user import User
from app.schemas.agentic_scheduling import (
    AgenticRecommendationDecisionRequest,
    AgenticRecommendationModifyRequest,
    AgenticRecommendationPublishRequest,
    AgenticScheduleEventRequest,
    AgenticScheduleRecommendationResponse,
    AgenticScheduleRecommendationView,
    ProductionScheduleVersionCompareResponse,
    ProductionScheduleVersionView,
)
from app.schemas.production_schedule import (
    ProductionCapacitySummaryResponse,
    ProductionScheduleGenerateRequest,
    ProductionScheduleResequenceRequest,
    ProductionScheduleResponse,
    ProductionScheduleStatusUpdateRequest,
)
from app.services.agentic_scheduling_service import AgenticSchedulingService
from app.services.production_schedule_service import ProductionScheduleService
from app.utils.security import decode_token


router = APIRouter(prefix="/production-scheduling", tags=["Production Scheduling"])

PLANNER_ROLES = ["admin", "supply_planner", "sop_coordinator"]
EXECUTION_ROLES = ["admin", "supply_planner", "sop_coordinator", "executive"]


def get_schedule_service(db: Session = Depends(get_db)) -> ProductionScheduleService:
    return ProductionScheduleService(db)


def get_agentic_service(db: Session = Depends(get_db)) -> AgenticSchedulingService:
    return AgenticSchedulingService(db)


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


@router.post(
    "/events/recommendation",
    response_model=AgenticScheduleRecommendationResponse,
)
def recommend_from_event(
    body: AgenticScheduleEventRequest,
    service: AgenticSchedulingService = Depends(get_agentic_service),
    current_user: User = Depends(require_roles(PLANNER_ROLES)),
):
    return service.recommend_for_event(body=body, user_id=current_user.id)


@router.get(
    "/recommendations",
    response_model=List[AgenticScheduleRecommendationView],
)
def list_event_recommendations(
    status: Optional[str] = None,
    supply_plan_id: Optional[int] = None,
    product_id: Optional[int] = None,
    service: AgenticSchedulingService = Depends(get_agentic_service),
    _: User = Depends(get_current_user),
):
    return service.list_recommendations(
        status=status,
        supply_plan_id=supply_plan_id,
        product_id=product_id,
    )


@router.get(
    "/recommendations/{recommendation_id}",
    response_model=AgenticScheduleRecommendationView,
)
def get_event_recommendation(
    recommendation_id: str,
    service: AgenticSchedulingService = Depends(get_agentic_service),
    _: User = Depends(get_current_user),
):
    return service.get_recommendation(recommendation_id)


@router.post(
    "/recommendations/{recommendation_id}/approve",
    response_model=AgenticScheduleRecommendationView,
)
def approve_event_recommendation(
    recommendation_id: str,
    body: AgenticRecommendationDecisionRequest,
    service: AgenticSchedulingService = Depends(get_agentic_service),
    current_user: User = Depends(require_roles(PLANNER_ROLES)),
):
    return service.approve_recommendation(
        recommendation_id=recommendation_id,
        body=body,
        user_id=current_user.id,
    )


@router.post(
    "/recommendations/{recommendation_id}/reject",
    response_model=AgenticScheduleRecommendationView,
)
def reject_event_recommendation(
    recommendation_id: str,
    body: AgenticRecommendationDecisionRequest,
    service: AgenticSchedulingService = Depends(get_agentic_service),
    current_user: User = Depends(require_roles(PLANNER_ROLES)),
):
    return service.reject_recommendation(
        recommendation_id=recommendation_id,
        body=body,
        user_id=current_user.id,
    )


@router.post(
    "/recommendations/{recommendation_id}/modify",
    response_model=AgenticScheduleRecommendationView,
)
def modify_event_recommendation(
    recommendation_id: str,
    body: AgenticRecommendationModifyRequest,
    service: AgenticSchedulingService = Depends(get_agentic_service),
    current_user: User = Depends(require_roles(PLANNER_ROLES)),
):
    return service.modify_recommendation(
        recommendation_id=recommendation_id,
        body=body,
        user_id=current_user.id,
    )


@router.post(
    "/recommendations/{recommendation_id}/publish",
    response_model=AgenticScheduleRecommendationView,
)
def publish_event_recommendation(
    recommendation_id: str,
    body: AgenticRecommendationPublishRequest,
    service: AgenticSchedulingService = Depends(get_agentic_service),
    current_user: User = Depends(require_roles(PLANNER_ROLES)),
):
    return service.publish_recommendation(
        recommendation_id=recommendation_id,
        body=body,
        user_id=current_user.id,
    )


@router.get(
    "/schedule-versions",
    response_model=List[ProductionScheduleVersionView],
)
def list_schedule_versions(
    supply_plan_id: int,
    service: AgenticSchedulingService = Depends(get_agentic_service),
    _: User = Depends(get_current_user),
):
    return service.list_schedule_versions(supply_plan_id=supply_plan_id)


@router.get(
    "/schedule-versions/compare",
    response_model=ProductionScheduleVersionCompareResponse,
)
def compare_schedule_versions(
    supply_plan_id: int,
    base_version: int,
    target_version: int,
    service: AgenticSchedulingService = Depends(get_agentic_service),
    _: User = Depends(get_current_user),
):
    return service.compare_schedule_versions(
        supply_plan_id=supply_plan_id,
        base_version=base_version,
        target_version=target_version,
    )


@router.get("/recommendations-stream")
async def stream_event_recommendations(
    request: Request,
    access_token: str = Query(..., description="JWT access token for SSE auth"),
    recommendation_status: Optional[str] = Query(default=None, alias="status"),
    supply_plan_id: Optional[int] = None,
    product_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    payload = decode_token(access_token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id), User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    if user.role not in EXECUTION_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    service = AgenticSchedulingService(db)

    async def event_generator() -> AsyncGenerator[str, None]:
        last_signature = ""
        while True:
            if await request.is_disconnected():
                break

            rows = service.list_recommendations(
                status=recommendation_status,
                supply_plan_id=supply_plan_id,
                product_id=product_id,
            )
            payload_rows = [r.model_dump(mode="json") for r in rows]
            signature = json.dumps(payload_rows, sort_keys=True)

            if signature != last_signature:
                last_signature = signature
                data = {
                    "count": len(payload_rows),
                    "recommendations": payload_rows,
                }
                yield f"event: recommendations\ndata: {json.dumps(data)}\n\n"
            else:
                yield ": keep-alive\n\n"

            await asyncio.sleep(5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
