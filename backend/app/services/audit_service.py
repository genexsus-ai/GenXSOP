from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import EntityNotFoundException, to_http_exception
from app.models.agentic_schedule_recommendation import AgenticScheduleRecommendation
from app.models.comment import AuditLog
from app.schemas.agentic_scheduling import AgenticScheduleRecommendationView
from app.schemas.audit import AuditDecisionView, RecommendationAuditTrailResponse
from app.services.agentic_scheduling_service import AgenticSchedulingService


class AuditService:
    def __init__(self, db: Session):
        self._db = db
        self._agentic_service = AgenticSchedulingService(db)

    def list_decisions(
        self,
        *,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[AuditDecisionView]:
        q = self._db.query(AuditLog)
        if entity_type:
            q = q.filter(AuditLog.entity_type == entity_type)
        if entity_id is not None:
            q = q.filter(AuditLog.entity_id == entity_id)
        rows = q.order_by(AuditLog.created_at.desc()).limit(limit).all()
        return [AuditDecisionView.model_validate(r) for r in rows]

    def get_recommendation_audit_trail(self, recommendation_id: str) -> RecommendationAuditTrailResponse:
        root = (
            self._db.query(AgenticScheduleRecommendation)
            .filter(AgenticScheduleRecommendation.recommendation_id == recommendation_id)
            .first()
        )
        if not root:
            raise to_http_exception(EntityNotFoundException("AgenticScheduleRecommendation", recommendation_id))

        chain_rows = (
            self._db.query(AgenticScheduleRecommendation)
            .filter(
                (AgenticScheduleRecommendation.recommendation_id == recommendation_id)
                | (AgenticScheduleRecommendation.source_recommendation_id == recommendation_id)
            )
            .order_by(AgenticScheduleRecommendation.revision_number.asc(), AgenticScheduleRecommendation.created_at.asc())
            .all()
        )

        revisions: List[AgenticScheduleRecommendationView] = [
            self._agentic_service._to_view(r) for r in chain_rows
        ]

        ids = [r.id for r in chain_rows]
        audit_rows = []
        if ids:
            audit_rows = (
                self._db.query(AuditLog)
                .filter(
                    AuditLog.entity_type.in_(["agentic_schedule_recommendation", "recommendation"]),
                    AuditLog.entity_id.in_(ids),
                )
                .order_by(AuditLog.created_at.asc())
                .all()
            )

        return RecommendationAuditTrailResponse(
            recommendation_id=recommendation_id,
            revisions=revisions,
            audit_logs=[AuditDecisionView.model_validate(a) for a in audit_rows],
        )
