"""
S&OP Cycle Service — Service Layer (SRP / DIP)
"""
import json
from math import ceil
from sqlalchemy.orm import Session

from app.repositories.sop_cycle_repository import SOPCycleRepository
from app.models.sop_cycle import SOPCycle
from app.schemas.sop_cycle import SOPCycleCreate, SOPCycleUpdate, SOPCycleListResponse
from app.core.exceptions import EntityNotFoundException, BusinessRuleViolationException, to_http_exception
from app.utils.events import get_event_bus, EntityCreatedEvent, EntityUpdatedEvent, PlanStatusChangedEvent


class SOPCycleService:

    def __init__(self, db: Session):
        self._repo = SOPCycleRepository(db)
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
