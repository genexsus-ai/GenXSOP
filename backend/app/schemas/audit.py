from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.schemas.agentic_scheduling import AgenticScheduleRecommendationView


class AuditDecisionView(BaseModel):
    id: int
    user_id: Optional[int] = None
    action: str
    entity_type: str
    entity_id: int
    old_values: Optional[str] = None
    new_values: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class RecommendationAuditTrailResponse(BaseModel):
    recommendation_id: str
    revisions: List[AgenticScheduleRecommendationView]
    audit_logs: List[AuditDecisionView]
