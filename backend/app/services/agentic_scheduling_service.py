from __future__ import annotations

import json
from datetime import datetime
from typing import List
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleViolationException, EntityNotFoundException, to_http_exception
from app.models.agentic_schedule_recommendation import AgenticScheduleRecommendation
from app.repositories.agentic_schedule_recommendation_repository import AgenticScheduleRecommendationRepository
from app.repositories.production_schedule_repository import ProductionScheduleRepository
from app.services.agentic_orchestration_service import AgenticOrchestrationService
from app.schemas.agentic_scheduling import (
    AgenticRecommendationDecisionRequest,
    AgenticScheduleAction,
    AgenticScheduleEventRequest,
    AgenticScheduleRecommendationResponse,
    AgenticScheduleRecommendationView,
)


class AgenticSchedulingService:
    """
    Initial event-driven recommendation service.
    This does not mutate schedule rows yet — it returns explainable,
    human-in-the-loop recommendations for planner approval.
    """

    def __init__(self, db: Session):
        self._db = db
        self._repo = ProductionScheduleRepository(db)
        self._recommendation_repo = AgenticScheduleRecommendationRepository(db)
        self._orchestrator = AgenticOrchestrationService()

    def recommend_for_event(
        self,
        body: AgenticScheduleEventRequest,
        user_id: int,
    ) -> AgenticScheduleRecommendationResponse:
        if body.supply_plan_id is None and body.product_id is None:
            raise to_http_exception(
                BusinessRuleViolationException(
                    "Provide supply_plan_id or product_id so impacted schedules can be evaluated."
                )
            )

        rows = self._repo.list_filtered(
            product_id=body.product_id,
            period=body.period,
            supply_plan_id=body.supply_plan_id,
            workcenter=body.workcenter,
            line=body.line,
            shift=body.shift,
        )

        if not rows:
            recommendation_id = str(uuid4())
            workflow_id = str(uuid4())
            payload = AgenticScheduleRecommendationResponse(
                recommendation_id=recommendation_id,
                workflow_id=workflow_id,
                state="PENDING_APPROVAL",
                event_type=body.event_type,
                severity=body.severity,
                impacted_rows=0,
                recommendation_summary="No impacted schedule rows found for this event context.",
                explanation=(
                    "The event was classified, but no production schedule rows matched the provided "
                    "scope (plan/product/period/workcenter/line/shift)."
                ),
                actions=[],
            )
            self._persist_recommendation(payload=payload, body=body, user_id=user_id)
            return payload

        actions = self._build_actions(body=body, schedule_ids=[r.id for r in rows], sequence_orders=[r.sequence_order for r in rows])
        recommendation = AgenticScheduleRecommendationResponse(
            recommendation_id=str(uuid4()),
            workflow_id=str(uuid4()),
            state="PENDING_APPROVAL",
            event_type=body.event_type,
            severity=body.severity,
            impacted_rows=len(rows),
            recommendation_summary=self._summary_text(body.event_type, len(actions), len(rows)),
            explanation=self._explanation_text(body.event_type, body.severity),
            actions=actions,
        )
        recommendation.orchestration = self._orchestrator.orchestrate(
            body=body,
            candidate_actions=actions,
        )
        self._persist_recommendation(payload=recommendation, body=body, user_id=user_id)
        return recommendation

    def list_recommendations(
        self,
        status: str | None = None,
        supply_plan_id: int | None = None,
        product_id: int | None = None,
    ) -> List[AgenticScheduleRecommendationView]:
        rows = self._recommendation_repo.list_filtered(
            status=status,
            supply_plan_id=supply_plan_id,
            product_id=product_id,
        )
        return [self._to_view(r) for r in rows]

    def get_recommendation(self, recommendation_id: str) -> AgenticScheduleRecommendationView:
        row = self._recommendation_repo.get_by_recommendation_id(recommendation_id)
        if not row:
            raise to_http_exception(EntityNotFoundException("AgenticScheduleRecommendation", recommendation_id))
        return self._to_view(row)

    def approve_recommendation(
        self,
        recommendation_id: str,
        body: AgenticRecommendationDecisionRequest,
        user_id: int,
    ) -> AgenticScheduleRecommendationView:
        row = self._recommendation_repo.get_by_recommendation_id(recommendation_id)
        if not row:
            raise to_http_exception(EntityNotFoundException("AgenticScheduleRecommendation", recommendation_id))
        if row.status != "pending_approval":
            raise to_http_exception(
                BusinessRuleViolationException(
                    f"Recommendation already decided with status '{row.status}'."
                )
            )
        row = self._recommendation_repo.update(
            row,
            {
                "status": "approved",
                "state": "APPROVED",
                "decision_note": body.note,
                "decided_by": user_id,
                "decided_at": datetime.utcnow(),
            },
        )
        return self._to_view(row)

    def reject_recommendation(
        self,
        recommendation_id: str,
        body: AgenticRecommendationDecisionRequest,
        user_id: int,
    ) -> AgenticScheduleRecommendationView:
        row = self._recommendation_repo.get_by_recommendation_id(recommendation_id)
        if not row:
            raise to_http_exception(EntityNotFoundException("AgenticScheduleRecommendation", recommendation_id))
        if row.status != "pending_approval":
            raise to_http_exception(
                BusinessRuleViolationException(
                    f"Recommendation already decided with status '{row.status}'."
                )
            )
        row = self._recommendation_repo.update(
            row,
            {
                "status": "rejected",
                "state": "REJECTED",
                "decision_note": body.note,
                "decided_by": user_id,
                "decided_at": datetime.utcnow(),
            },
        )
        return self._to_view(row)

    def _build_actions(
        self,
        body: AgenticScheduleEventRequest,
        schedule_ids: List[int],
        sequence_orders: List[int],
    ) -> List[AgenticScheduleAction]:
        max_seq = max(sequence_orders)
        min_seq = min(sequence_orders)

        if body.event_type in {"MACHINE_DOWN", "MATERIAL_SHORTAGE", "LABOR_UNAVAILABLE", "QUALITY_HOLD"}:
            target_id = schedule_ids[0]
            from_seq = sequence_orders[0]
            return [
                AgenticScheduleAction(
                    action_type="resequence",
                    schedule_id=target_id,
                    from_sequence=from_seq,
                    to_sequence=max_seq,
                    reason=f"{body.event_type} impact: de-prioritize affected slot to preserve feasible flow.",
                    confidence=0.78,
                )
            ]

        if body.event_type == "ORDER_PRIORITY_CHANGED":
            target_idx = 0
            for idx, seq in enumerate(sequence_orders):
                if seq > min_seq:
                    target_idx = idx
                    break
            return [
                AgenticScheduleAction(
                    action_type="expedite",
                    schedule_id=schedule_ids[target_idx],
                    from_sequence=sequence_orders[target_idx],
                    to_sequence=min_seq,
                    reason="Urgent order signal: prioritize earlier execution.",
                    confidence=0.82,
                )
            ]

        if body.event_type in {"MACHINE_RECOVERED", "QUALITY_RELEASED"}:
            target_id = schedule_ids[0]
            from_seq = sequence_orders[0]
            to_seq = max(min_seq, from_seq - 1)
            return [
                AgenticScheduleAction(
                    action_type="resequence",
                    schedule_id=target_id,
                    from_sequence=from_seq,
                    to_sequence=to_seq,
                    reason=f"{body.event_type} recovered constrained capacity; consider earlier placement.",
                    confidence=0.7,
                )
            ]

        return [
            AgenticScheduleAction(
                action_type="manual_review",
                schedule_id=schedule_ids[0],
                from_sequence=sequence_orders[0],
                to_sequence=sequence_orders[0],
                reason="Event requires planner decision before automatic resequencing.",
                confidence=0.6,
            )
        ]

    @staticmethod
    def _summary_text(event_type: str, action_count: int, impacted_rows: int) -> str:
        return (
            f"Event {event_type} classified. Generated {action_count} recommendation(s) "
            f"for {impacted_rows} impacted schedule row(s)."
        )

    @staticmethod
    def _explanation_text(event_type: str, severity: str) -> str:
        return (
            f"Exception agent classified event as {event_type} (severity={severity}). "
            "Planner/constraint heuristics produced a candidate action with confidence scoring. "
            "Recommendation remains in pending approval state for human-in-the-loop control."
        )

    def _persist_recommendation(
        self,
        payload: AgenticScheduleRecommendationResponse,
        body: AgenticScheduleEventRequest,
        user_id: int,
    ) -> AgenticScheduleRecommendation:
        row = AgenticScheduleRecommendation(
            recommendation_id=payload.recommendation_id,
            workflow_id=payload.workflow_id,
            event_type=payload.event_type,
            severity=payload.severity,
            event_timestamp=body.event_timestamp,
            supply_plan_id=body.supply_plan_id,
            product_id=body.product_id,
            period=body.period,
            workcenter=body.workcenter,
            line=body.line,
            shift=body.shift,
            impacted_rows=payload.impacted_rows,
            recommendation_summary=payload.recommendation_summary,
            explanation=payload.explanation,
            actions_json=json.dumps([a.model_dump() for a in payload.actions]),
            state=payload.state,
            status="pending_approval",
            created_by=user_id,
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def _to_view(self, row: AgenticScheduleRecommendation) -> AgenticScheduleRecommendationView:
        try:
            actions_raw = json.loads(row.actions_json) if row.actions_json else []
        except Exception:
            actions_raw = []

        actions = [AgenticScheduleAction(**a) for a in actions_raw]
        return AgenticScheduleRecommendationView(
            recommendation_id=row.recommendation_id,
            workflow_id=row.workflow_id,
            event_type=row.event_type,
            severity=row.severity,
            status=row.status,
            state=row.state,
            impacted_rows=row.impacted_rows,
            recommendation_summary=row.recommendation_summary,
            explanation=row.explanation,
            actions=actions,
            decision_note=row.decision_note,
            decided_at=row.decided_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
