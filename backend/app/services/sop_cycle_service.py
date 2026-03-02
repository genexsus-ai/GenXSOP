"""
S&OP Cycle Service — Service Layer (SRP / DIP)
"""
import json
from math import ceil
from sqlalchemy.orm import Session

from app.repositories.sop_cycle_repository import SOPCycleRepository
from app.repositories.scenario_repository import ScenarioRepository
from app.repositories.inventory_exception_repository import InventoryExceptionRepository
from app.repositories.inventory_recommendation_repository import InventoryRecommendationRepository
from app.models.sop_cycle import SOPCycle
from app.schemas.sop_cycle import (
    SOPCycleCreate,
    SOPCycleUpdate,
    SOPCycleListResponse,
    SOPExecutiveScorecard,
    SOPExecutiveServiceView,
    SOPExecutiveCostView,
    SOPExecutiveCashView,
    SOPExecutiveRiskView,
)
from app.core.exceptions import EntityNotFoundException, BusinessRuleViolationException, to_http_exception
from app.utils.events import get_event_bus, EntityCreatedEvent, EntityUpdatedEvent, PlanStatusChangedEvent


class SOPCycleService:

    def __init__(self, db: Session):
        self._repo = SOPCycleRepository(db)
        self._scenario_repo = ScenarioRepository(db)
        self._exception_repo = InventoryExceptionRepository(db)
        self._recommendation_repo = InventoryRecommendationRepository(db)
        self._bus = get_event_bus()

    def list_cycles(self, page: int = 1, page_size: int = 20) -> SOPCycleListResponse:
        items, total = self._repo.list_paginated(page=page, page_size=page_size)
        return SOPCycleListResponse(
            items=items, total=total, page=page, page_size=page_size,
            total_pages=ceil(total / page_size) if total else 0,
        )

    def get_cycle(self, cycle_id: int) -> SOPCycle:
        cycle = self._repo.get_by_id(cycle_id)
        if not cycle:
            raise to_http_exception(EntityNotFoundException("SOPCycle", cycle_id))
        return cycle

    def get_active_cycle(self):
        return self._repo.get_active_cycle()

    def create_cycle(self, data: SOPCycleCreate, created_by: int) -> SOPCycle:
        cycle = SOPCycle(**data.model_dump())
        result = self._repo.create(cycle)
        self._bus.publish(EntityCreatedEvent(
            entity_type="sop_cycle", entity_id=result.id, user_id=created_by,
        ))
        return result

    def update_cycle(self, cycle_id: int, data: SOPCycleUpdate, user_id: int) -> SOPCycle:
        cycle = self.get_cycle(cycle_id)
        updates = data.model_dump(exclude_unset=True)
        result = self._repo.update(cycle, updates)
        self._bus.publish(EntityUpdatedEvent(
            entity_type="sop_cycle", entity_id=cycle_id, user_id=user_id, new_values=updates,
        ))
        return result

    def advance_step(self, cycle_id: int, user_id: int) -> SOPCycle:
        """Advance the S&OP cycle to the next step (1→2→3→4→5)."""
        cycle = self.get_cycle(cycle_id)
        if cycle.overall_status != "active":
            raise to_http_exception(
                BusinessRuleViolationException("Can only advance an active S&OP cycle.")
            )
        if cycle.current_step >= 5:
            raise to_http_exception(
                BusinessRuleViolationException("S&OP cycle is already at the final step (Executive S&OP).")
            )
        step_map = {
            1: "step_1_status",
            2: "step_2_status",
            3: "step_3_status",
            4: "step_4_status",
            5: "step_5_status",
        }
        current_step_field = step_map[cycle.current_step]
        next_step = cycle.current_step + 1
        updates = {
            current_step_field: "completed",
            "current_step": next_step,
        }
        result = self._repo.update(cycle, updates)
        self._bus.publish(PlanStatusChangedEvent(
            entity_type="sop_cycle", entity_id=cycle_id, user_id=user_id,
            old_status=f"step_{cycle.current_step}",
            new_status=f"step_{next_step}",
        ))
        return result

    def complete_cycle(self, cycle_id: int, user_id: int) -> SOPCycle:
        """Mark the entire S&OP cycle as completed."""
        cycle = self.get_cycle(cycle_id)
        updates = {
            "step_5_status": "completed",
            "overall_status": "completed",
        }
        result = self._repo.update(cycle, updates)
        self._bus.publish(PlanStatusChangedEvent(
            entity_type="sop_cycle", entity_id=cycle_id, user_id=user_id,
            old_status="active", new_status="completed",
        ))
        return result

    def get_executive_scorecard(self, cycle_id: int) -> SOPExecutiveScorecard:
        cycle = self.get_cycle(cycle_id)

        completed = self._scenario_repo.get_by_status("completed")
        approved = self._scenario_repo.get_by_status("approved")
        candidates = completed + approved

        selected = None
        for s in candidates:
            try:
                results = json.loads(s.results) if isinstance(s.results, str) else (s.results or {})
                if results.get("period") == cycle.period.isoformat():
                    selected = s
                    break
            except Exception:
                continue
        if selected is None and candidates:
            selected = candidates[0]

        results = {}
        if selected and selected.results:
            try:
                results = json.loads(selected.results) if isinstance(selected.results, str) else (selected.results or {})
            except Exception:
                results = {}

        baseline = results.get("baseline", {})
        scenario = results.get("scenario", {})
        tradeoff = results.get("tradeoff", {})

        open_ex = self._exception_repo.list_filtered(status="open")
        in_prog_ex = self._exception_repo.list_filtered(status="in_progress")
        open_total = len(open_ex) + len(in_prog_ex)
        high_risk = len([e for e in (open_ex + in_prog_ex) if e.severity == "high"])
        pending_recs = len(self._recommendation_repo.list_filtered(status="pending"))

        if pending_recs > 50 or high_risk > 20:
            backlog_risk = "high"
        elif pending_recs > 20 or high_risk > 5:
            backlog_risk = "medium"
        else:
            backlog_risk = "low"

        service_delta = float((scenario.get("service_level", 0) or 0) - (baseline.get("service_level", 0) or 0))
        composite = float(tradeoff.get("composite_score", 0) or 0)
        if service_delta >= 1 and composite >= 0 and backlog_risk != "high":
            decision_signal = "recommended"
        elif service_delta < 0 and backlog_risk == "high":
            decision_signal = "not_recommended"
        else:
            decision_signal = "review_required"

        return SOPExecutiveScorecard(
            cycle_id=cycle.id,
            cycle_name=cycle.cycle_name,
            period=cycle.period,
            scenario_reference=getattr(selected, "name", None),
            service=SOPExecutiveServiceView(
                baseline_service_level=float(baseline.get("service_level", 0) or 0),
                scenario_service_level=float(scenario.get("service_level", 0) or 0),
                delta_service_level=service_delta,
            ),
            cost=SOPExecutiveCostView(
                inventory_carrying_cost=float(tradeoff.get("inventory_carrying_cost", 0) or 0),
                stockout_penalty_cost=float(tradeoff.get("stockout_penalty_cost", 0) or 0),
                composite_tradeoff_score=composite,
            ),
            cash=SOPExecutiveCashView(
                working_capital_delta=float(tradeoff.get("working_capital_delta", 0) or 0),
                inventory_value_estimate=float(scenario.get("inventory_value", 0) or 0),
            ),
            risk=SOPExecutiveRiskView(
                open_exceptions=open_total,
                high_risk_exceptions=high_risk,
                pending_recommendations=pending_recs,
                backlog_risk=backlog_risk,
            ),
            decision_signal=decision_signal,
        )
