from __future__ import annotations

import json
from datetime import datetime
from typing import List
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleViolationException, EntityNotFoundException, to_http_exception
from app.models.agentic_schedule_recommendation import AgenticScheduleRecommendation
from app.models.production_schedule_snapshot import ProductionScheduleSnapshot
from app.repositories.agentic_schedule_recommendation_repository import AgenticScheduleRecommendationRepository
from app.repositories.production_schedule_repository import ProductionScheduleRepository
from app.repositories.production_schedule_snapshot_repository import ProductionScheduleSnapshotRepository
from app.services.agentic_orchestration_service import AgenticOrchestrationService
from app.schemas.agentic_scheduling import (
    AgenticRecommendationDecisionRequest,
    AgenticRecommendationModifyRequest,
    AgenticRecommendationPublishRequest,
    ProductionScheduleVersionCompareResponse,
    ProductionScheduleVersionView,
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
        self._snapshot_repo = ProductionScheduleSnapshotRepository(db)
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

    def modify_recommendation(
        self,
        recommendation_id: str,
        body: AgenticRecommendationModifyRequest,
        user_id: int,
    ) -> AgenticScheduleRecommendationView:
        row = self._recommendation_repo.get_by_recommendation_id(recommendation_id)
        if not row:
            raise to_http_exception(EntityNotFoundException("AgenticScheduleRecommendation", recommendation_id))
        if row.status != "pending_approval":
            raise to_http_exception(
                BusinessRuleViolationException(
                    f"Only pending_approval recommendations can be modified (current={row.status})."
                )
            )

        revised_actions = body.actions or self._actions_from_json(row.actions_json)
        revised_summary = body.recommendation_summary or row.recommendation_summary
        next_revision = self._recommendation_repo.max_revision_for_chain(recommendation_id) + 1

        clone = AgenticScheduleRecommendation(
            recommendation_id=str(uuid4()),
            workflow_id=str(uuid4()),
            event_type=row.event_type,
            severity=row.severity,
            event_timestamp=row.event_timestamp,
            supply_plan_id=row.supply_plan_id,
            product_id=row.product_id,
            period=row.period,
            workcenter=row.workcenter,
            line=row.line,
            shift=row.shift,
            impacted_rows=row.impacted_rows,
            recommendation_summary=revised_summary,
            explanation=row.explanation,
            actions_json=json.dumps([a.model_dump() for a in revised_actions]),
            state="PENDING_APPROVAL",
            status="pending_approval",
            decision_note=body.note,
            source_recommendation_id=recommendation_id,
            revision_number=next_revision,
            created_by=user_id,
        )
        self._db.add(clone)
        self._db.commit()
        self._db.refresh(clone)
        return self._to_view(clone)

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

    def publish_recommendation(
        self,
        recommendation_id: str,
        body: AgenticRecommendationPublishRequest,
        user_id: int,
    ) -> AgenticScheduleRecommendationView:
        row = self._recommendation_repo.get_by_recommendation_id(recommendation_id)
        if not row:
            raise to_http_exception(EntityNotFoundException("AgenticScheduleRecommendation", recommendation_id))
        if row.status != "approved":
            raise to_http_exception(
                BusinessRuleViolationException(
                    f"Only approved recommendations can be published (current={row.status})."
                )
            )

        actions = self._actions_from_json(row.actions_json)
        if body.apply_actions:
            self._apply_actions(actions)

        version = self._persist_snapshot(
            supply_plan_id=row.supply_plan_id,
            recommendation_id=row.recommendation_id,
            user_id=user_id,
        )

        note = body.note or f"Published as schedule version {version.version_number}."
        row = self._recommendation_repo.update(
            row,
            {
                "status": "published",
                "state": "PUBLISHED",
                "decision_note": note,
                "published_by": user_id,
                "published_at": datetime.utcnow(),
            },
        )
        return self._to_view(row)

    def list_schedule_versions(self, supply_plan_id: int) -> List[ProductionScheduleVersionView]:
        rows = self._snapshot_repo.list_by_supply_plan(supply_plan_id)
        return [
            ProductionScheduleVersionView(
                supply_plan_id=r.supply_plan_id,
                version_number=r.version_number,
                recommendation_id=r.recommendation_id,
                published_by=r.published_by,
                published_at=r.published_at,
            )
            for r in rows
        ]

    def compare_schedule_versions(
        self,
        supply_plan_id: int,
        base_version: int,
        target_version: int,
    ) -> ProductionScheduleVersionCompareResponse:
        base_row = self._snapshot_repo.get_by_supply_plan_and_version(supply_plan_id, base_version)
        target_row = self._snapshot_repo.get_by_supply_plan_and_version(supply_plan_id, target_version)
        if not base_row:
            raise to_http_exception(EntityNotFoundException("ProductionScheduleSnapshot(base)", base_version))
        if not target_row:
            raise to_http_exception(EntityNotFoundException("ProductionScheduleSnapshot(target)", target_version))

        base_items = json.loads(base_row.snapshot_json)
        target_items = json.loads(target_row.snapshot_json)

        base_map = {int(item["id"]): item for item in base_items}
        changed_ids: list[int] = []
        for item in target_items:
            sid = int(item["id"])
            if sid not in base_map:
                changed_ids.append(sid)
                continue
            if (
                item.get("sequence_order") != base_map[sid].get("sequence_order")
                or str(item.get("planned_start_at")) != str(base_map[sid].get("planned_start_at"))
                or str(item.get("planned_end_at")) != str(base_map[sid].get("planned_end_at"))
            ):
                changed_ids.append(sid)

        return ProductionScheduleVersionCompareResponse(
            supply_plan_id=supply_plan_id,
            base_version=base_version,
            target_version=target_version,
            changed_rows=len(changed_ids),
            changed_schedule_ids=sorted(changed_ids),
        )

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
            state="SIMULATED",
            status="pending_approval",
            created_by=user_id,
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def _actions_from_json(self, actions_json: str) -> List[AgenticScheduleAction]:
        try:
            raw = json.loads(actions_json) if actions_json else []
        except Exception:
            raw = []
        return [AgenticScheduleAction(**a) for a in raw]

    def _apply_actions(self, actions: List[AgenticScheduleAction]) -> None:
        for action in actions:
            row = self._repo.get_by_id(action.schedule_id)
            if not row:
                continue
            row.sequence_order = max(1, int(action.to_sequence))
            if action.action_type in {"expedite", "resequence"}:
                row.status = "released"
        self._db.commit()

    def _persist_snapshot(
        self,
        supply_plan_id: int | None,
        recommendation_id: str,
        user_id: int,
    ) -> ProductionScheduleSnapshot:
        if not supply_plan_id:
            raise to_http_exception(BusinessRuleViolationException("Cannot publish without supply_plan_id."))

        rows = self._repo.list_filtered(supply_plan_id=supply_plan_id)
        payload = [
            {
                "id": r.id,
                "sequence_order": r.sequence_order,
                "status": r.status,
                "planned_start_at": r.planned_start_at.isoformat() if r.planned_start_at else None,
                "planned_end_at": r.planned_end_at.isoformat() if r.planned_end_at else None,
            }
            for r in rows
        ]

        latest = self._snapshot_repo.latest_for_supply_plan(supply_plan_id)
        next_version = (latest.version_number + 1) if latest else 1

        snapshot = ProductionScheduleSnapshot(
            supply_plan_id=supply_plan_id,
            version_number=next_version,
            recommendation_id=recommendation_id,
            snapshot_json=json.dumps(payload),
            published_by=user_id,
            published_at=datetime.utcnow(),
        )
        self._db.add(snapshot)
        self._db.commit()
        self._db.refresh(snapshot)
        return snapshot

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
            source_recommendation_id=row.source_recommendation_id,
            revision_number=row.revision_number,
            published_at=row.published_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
