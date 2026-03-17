from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


AgenticEventType = Literal[
    "MACHINE_DOWN",
    "MACHINE_RECOVERED",
    "ORDER_PRIORITY_CHANGED",
    "MATERIAL_SHORTAGE",
    "QUALITY_HOLD",
    "QUALITY_RELEASED",
    "LABOR_UNAVAILABLE",
]

AgenticSeverity = Literal["low", "medium", "high", "critical"]
AgenticRecommendationStatus = Literal["pending_approval", "approved", "rejected"]


class AgenticScheduleEventRequest(BaseModel):
    event_type: AgenticEventType
    severity: AgenticSeverity = "medium"
    event_timestamp: datetime

    supply_plan_id: Optional[int] = None
    product_id: Optional[int] = None
    period: Optional[date] = None

    workcenter: Optional[str] = None
    line: Optional[str] = None
    shift: Optional[str] = None

    note: Optional[str] = None


class AgenticScheduleAction(BaseModel):
    action_type: Literal["resequence", "expedite", "hold", "manual_review"]
    schedule_id: int
    from_sequence: int
    to_sequence: int
    reason: str
    confidence: float = Field(ge=0, le=1)


class AgenticScheduleRecommendationResponse(BaseModel):
    recommendation_id: str
    workflow_id: str
    state: Literal["RECEIVED", "CLASSIFIED", "PENDING_APPROVAL"]

    event_type: AgenticEventType
    severity: AgenticSeverity
    impacted_rows: int

    recommendation_summary: str
    explanation: str
    actions: List[AgenticScheduleAction]
    orchestration: Optional["AgenticOrchestrationResponse"] = None


class AgenticScheduleRecommendationView(BaseModel):
    recommendation_id: str
    workflow_id: str
    event_type: AgenticEventType
    severity: AgenticSeverity
    status: AgenticRecommendationStatus
    state: str
    impacted_rows: int
    recommendation_summary: str
    explanation: str
    actions: List[AgenticScheduleAction]
    decision_note: Optional[str] = None
    decided_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class AgenticRecommendationDecisionRequest(BaseModel):
    note: Optional[str] = None


class AgenticOrchestrationAlternative(BaseModel):
    action: AgenticScheduleAction
    score: float
    simulated_kpis: dict


class AgenticOrchestrationResponse(BaseModel):
    workflow_state: Literal["FAILED", "SIMULATED"]
    recommendation_summary: str
    selected_action: Optional[AgenticScheduleAction] = None
    alternatives: List[AgenticOrchestrationAlternative]


AgenticScheduleRecommendationResponse.model_rebuild()
