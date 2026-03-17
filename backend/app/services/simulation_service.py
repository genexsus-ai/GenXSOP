import json
from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleViolationException, EntityNotFoundException, to_http_exception
from app.models.agentic_schedule_recommendation import AgenticScheduleRecommendation
from app.models.simulation_run import SimulationRun
from app.repositories.simulation_run_repository import SimulationRunRepository
from app.schemas.agentic_scheduling import AgenticScheduleAction, AgenticScheduleEventRequest
from app.schemas.simulation import SimulationRunCreateRequest, SimulationRunResponse
from app.services.agentic_orchestration_service import AgenticOrchestrationService


class SimulationService:
    def __init__(self, db: Session):
        self._db = db
        self._repo = SimulationRunRepository(db)
        self._orchestrator = AgenticOrchestrationService()

    def run_simulation(self, body: SimulationRunCreateRequest, user_id: int) -> SimulationRunResponse:
        recommendation = None
        if body.recommendation_id:
            recommendation = (
                self._db.query(AgenticScheduleRecommendation)
                .filter(AgenticScheduleRecommendation.recommendation_id == body.recommendation_id)
                .first()
            )
            if not recommendation:
                raise to_http_exception(EntityNotFoundException("AgenticScheduleRecommendation", body.recommendation_id))

            actions_raw = json.loads(recommendation.actions_json or "[]")
            if not actions_raw:
                raise to_http_exception(BusinessRuleViolationException("Recommendation has no actions to simulate."))
            action = AgenticScheduleAction(**actions_raw[0])
            event = AgenticScheduleEventRequest(
                event_type=recommendation.event_type,
                severity=recommendation.severity,
                event_timestamp=recommendation.event_timestamp,
                supply_plan_id=recommendation.supply_plan_id,
                product_id=recommendation.product_id,
                period=recommendation.period,
                workcenter=recommendation.workcenter,
                line=recommendation.line,
                shift=recommendation.shift,
                note=f"Simulation for recommendation {recommendation.recommendation_id}",
            )
        else:
            if not body.event_type or not body.severity or not body.action:
                raise to_http_exception(
                    BusinessRuleViolationException(
                        "Provide recommendation_id, or provide event_type+severity+action for direct simulation."
                    )
                )
            action = body.action
            event = AgenticScheduleEventRequest(
                event_type=body.event_type,
                severity=body.severity,
                event_timestamp=datetime.utcnow(),
            )

        orchestration = self._orchestrator.orchestrate(body=event, candidate_actions=[action])

        sim_id = str(uuid4())
        run = SimulationRun(
            simulation_id=sim_id,
            recommendation_id=body.recommendation_id if body.recommendation_id else None,
            scenario_name=body.scenario_name,
            status="completed" if orchestration.workflow_state != "FAILED" else "failed",
            request_json=body.model_dump_json(),
            result_json=orchestration.model_dump_json(),
            error=None if orchestration.workflow_state != "FAILED" else "No feasible alternatives",
            created_by=user_id,
            completed_at=datetime.utcnow(),
        )
        self._db.add(run)
        self._db.commit()
        self._db.refresh(run)
        return self._to_response(run)

    def get_simulation(self, simulation_id: str) -> SimulationRunResponse:
        row = self._repo.get_by_simulation_id(simulation_id)
        if not row:
            raise to_http_exception(EntityNotFoundException("SimulationRun", simulation_id))
        return self._to_response(row)

    def list_simulations(
        self,
        recommendation_id: str | None = None,
        status: str | None = None,
        scenario_name: str | None = None,
        limit: int = 100,
    ) -> list[SimulationRunResponse]:
        rows = self._repo.list_filtered(
            recommendation_id=recommendation_id,
            status=status,
            scenario_name=scenario_name,
            limit=limit,
        )
        return [self._to_response(row) for row in rows]

    @staticmethod
    def _to_response(row: SimulationRun) -> SimulationRunResponse:
        result = None
        if row.result_json:
            result = json.loads(row.result_json)
        return SimulationRunResponse(
            simulation_id=row.simulation_id,
            recommendation_id=row.recommendation_id,
            scenario_name=row.scenario_name,
            status=row.status,
            result=result,
            error=row.error,
            created_at=row.created_at,
            completed_at=row.completed_at,
        )
