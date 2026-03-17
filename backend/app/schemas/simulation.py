from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.agentic_scheduling import (
    AgenticOrchestrationResponse,
    AgenticScheduleAction,
    AgenticEventType,
    AgenticSeverity,
)


class SimulationRunCreateRequest(BaseModel):
    recommendation_id: Optional[str] = None
    scenario_name: Optional[str] = Field(default="what-if")
    event_type: Optional[AgenticEventType] = None
    severity: Optional[AgenticSeverity] = None
    action: Optional[AgenticScheduleAction] = None


class SimulationRunResponse(BaseModel):
    simulation_id: str
    recommendation_id: Optional[str] = None
    scenario_name: Optional[str] = None
    status: str
    result: Optional[AgenticOrchestrationResponse] = None
    error: Optional[str] = None
    created_at: datetime
    completed_at: datetime
