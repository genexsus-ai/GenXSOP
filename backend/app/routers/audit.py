from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.audit import AuditDecisionView, RecommendationAuditTrailResponse
from app.services.audit_service import AuditService


router = APIRouter(prefix="/audit", tags=["Audit"])


def get_audit_service(db: Session = Depends(get_db)) -> AuditService:
    return AuditService(db)


@router.get("/decisions", response_model=list[AuditDecisionView])
def list_audit_decisions(
    entity_type: Optional[str] = Query(default=None),
    entity_id: Optional[int] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    service: AuditService = Depends(get_audit_service),
    _: User = Depends(get_current_user),
):
    return service.list_decisions(entity_type=entity_type, entity_id=entity_id, limit=limit)


@router.get("/recommendations/{recommendation_id}", response_model=RecommendationAuditTrailResponse)
def get_recommendation_audit_trail(
    recommendation_id: str,
    service: AuditService = Depends(get_audit_service),
    _: User = Depends(get_current_user),
):
    return service.get_recommendation_audit_trail(recommendation_id)
