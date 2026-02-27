"""
Demand Service — Service Layer (SRP / DIP)

Principles applied:
- Single Responsibility Principle (SRP): Only handles demand planning business logic.
- Dependency Inversion Principle (DIP): Depends on DemandPlanRepository abstraction, not SQLAlchemy directly.
- Open/Closed Principle (OCP): Extend by subclassing or adding methods, not modifying existing logic.
"""
from math import ceil
from typing import Optional
from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Session

from app.repositories.demand_repository import DemandPlanRepository
from app.models.demand_plan import DemandPlan
from app.schemas.demand import (
    DemandPlanCreate, DemandPlanUpdate, DemandPlanListResponse,
    AdjustmentRequest, ApprovalRequest,
)
from app.core.exceptions import (
    EntityNotFoundException,
    BusinessRuleViolationException,
    InvalidStateTransitionException,
    to_http_exception,
)
from app.utils.events import get_event_bus, EntityCreatedEvent, EntityUpdatedEvent, EntityDeletedEvent, PlanStatusChangedEvent


class DemandService:
    """
    Encapsulates all demand planning business logic.
    Routers call this service; they never touch the DB directly.
    """

    def __init__(self, db: Session):
        self._repo = DemandPlanRepository(db)
        self._bus = get_event_bus()

    # ── Queries ───────────────────────────────────────────────────────────────

    def list_plans(
        self,
        page: int = 1,
        page_size: int = 20,
        product_id: Optional[int] = None,
        region: Optional[str] = None,
        channel: Optional[str] = None,
        status: Optional[str] = None,
        period_from: Optional[date] = None,
        period_to: Optional[date] = None,
    ) -> DemandPlanListResponse:
        items, total = self._repo.list_paginated(
            page=page, page_size=page_size,
            product_id=product_id, region=region, channel=channel,
            status=status, period_from=period_from, period_to=period_to,
        )
        return DemandPlanListResponse(
            items=items, total=total, page=page, page_size=page_size,
            total_pages=ceil(total / page_size) if total else 0,
        )

    def get_plan(self, plan_id: int) -> DemandPlan:
        plan = self._repo.get_by_id(plan_id)
        if not plan:
            raise to_http_exception(EntityNotFoundException("DemandPlan", plan_id))
        return plan

    # ── Commands ──────────────────────────────────────────────────────────────

    def create_plan(self, data: DemandPlanCreate, created_by: int) -> DemandPlan:
        plan = DemandPlan(**data.model_dump(), created_by=created_by)
        result = self._repo.create(plan)
        self._bus.publish(EntityCreatedEvent(
            entity_type="demand_plan", entity_id=result.id, user_id=created_by,
            new_values={"product_id": result.product_id, "period": str(result.period)},
        ))
        return result

    def update_plan(self, plan_id: int, data: DemandPlanUpdate, user_id: int) -> DemandPlan:
        plan = self.get_plan(plan_id)
        if plan.status == "locked":
            raise to_http_exception(BusinessRuleViolationException("Cannot modify a locked demand plan."))
        old_vals = {"status": plan.status, "forecast_qty": str(plan.forecast_qty)}
        updates = data.model_dump(exclude_unset=True)
        updates["version"] = plan.version + 1
        result = self._repo.update(plan, updates)
        self._bus.publish(EntityUpdatedEvent(
            entity_type="demand_plan", entity_id=plan_id, user_id=user_id,
            old_values=old_vals, new_values=updates,
        ))
        return result

    def adjust_forecast(self, plan_id: int, body: AdjustmentRequest, user_id: int) -> DemandPlan:
        plan = self.get_plan(plan_id)
        updates = {"adjusted_qty": body.adjusted_qty, "version": plan.version + 1}
        if body.notes:
            updates["notes"] = body.notes
        result = self._repo.update(plan, updates)
        self._bus.publish(EntityUpdatedEvent(
            entity_type="demand_plan", entity_id=plan_id, user_id=user_id,
            old_values={"adjusted_qty": str(plan.adjusted_qty)},
            new_values={"adjusted_qty": str(body.adjusted_qty)},
        ))
        return result

    def submit_plan(self, plan_id: int, user_id: int) -> DemandPlan:
        plan = self.get_plan(plan_id)
        if plan.status != "draft":
            raise to_http_exception(
                InvalidStateTransitionException("DemandPlan", plan.status, "submitted")
            )
        result = self._repo.update(plan, {"status": "submitted"})
        self._bus.publish(PlanStatusChangedEvent(
            entity_type="demand_plan", entity_id=plan_id, user_id=user_id,
            old_status="draft", new_status="submitted",
        ))
        return result

    def approve_plan(self, plan_id: int, body: ApprovalRequest, approver_id: int) -> DemandPlan:
        plan = self.get_plan(plan_id)
        updates = {"status": "approved", "approved_by": approver_id}
        if body.comments:
            updates["notes"] = (plan.notes or "") + f"\n[Approved] {body.comments}"
        result = self._repo.update(plan, updates)
        self._bus.publish(PlanStatusChangedEvent(
            entity_type="demand_plan", entity_id=plan_id, user_id=approver_id,
            old_status=plan.status, new_status="approved", comment=body.comments,
        ))
        return result

    def reject_plan(self, plan_id: int, body: ApprovalRequest, approver_id: int) -> DemandPlan:
        plan = self.get_plan(plan_id)
        updates = {"status": "draft"}
        if body.comments:
            updates["notes"] = (plan.notes or "") + f"\n[Rejected] {body.comments}"
        result = self._repo.update(plan, updates)
        self._bus.publish(PlanStatusChangedEvent(
            entity_type="demand_plan", entity_id=plan_id, user_id=approver_id,
            old_status=plan.status, new_status="draft", comment=body.comments,
        ))
        return result

    def delete_plan(self, plan_id: int, user_id: int) -> None:
        plan = self.get_plan(plan_id)
        if plan.status in ("approved", "locked"):
            raise to_http_exception(
                BusinessRuleViolationException("Cannot delete approved or locked demand plans.")
            )
        self._repo.delete(plan)
        self._bus.publish(EntityDeletedEvent(
            entity_type="demand_plan", entity_id=plan_id, user_id=user_id,
        ))
