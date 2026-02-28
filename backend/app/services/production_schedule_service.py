from datetime import datetime, timedelta, date
from decimal import Decimal, ROUND_DOWN
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import (
    BusinessRuleViolationException,
    EntityNotFoundException,
    to_http_exception,
)
from app.models.production_schedule import ProductionSchedule
from app.repositories.production_schedule_repository import ProductionScheduleRepository
from app.repositories.supply_repository import SupplyPlanRepository
from app.schemas.production_schedule import (
    CapacityGroupSummary,
    ProductionScheduleGenerateRequest,
    ProductionCapacitySummaryResponse,
    ProductionScheduleResequenceRequest,
    ProductionScheduleStatusUpdateRequest,
)


class ProductionScheduleService:
    def __init__(self, db: Session):
        self._db = db
        self._repo = ProductionScheduleRepository(db)
        self._supply_repo = SupplyPlanRepository(db)

    def list_schedules(
        self,
        product_id: Optional[int] = None,
        period: Optional[date] = None,
        supply_plan_id: Optional[int] = None,
        workcenter: Optional[str] = None,
        line: Optional[str] = None,
        shift: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[ProductionSchedule]:
        return self._repo.list_filtered(
            product_id=product_id,
            period=period,
            supply_plan_id=supply_plan_id,
            workcenter=workcenter,
            line=line,
            shift=shift,
            status=status,
        )

    def generate_schedule(
        self,
        body: ProductionScheduleGenerateRequest,
        user_id: int,
    ) -> List[ProductionSchedule]:
        supply_plan = self._supply_repo.get_by_id(body.supply_plan_id)
        if not supply_plan:
            raise to_http_exception(EntityNotFoundException("SupplyPlan", body.supply_plan_id))

        workcenters = [w.strip() for w in body.workcenters if w and w.strip()]
        lines = [l.strip() for l in body.lines if l and l.strip()]
        shifts = [s.strip() for s in body.shifts if s and s.strip()]
        if not workcenters or not lines or not shifts:
            raise to_http_exception(
                BusinessRuleViolationException("At least one workcenter, line, and shift is required.")
            )

        slots: list[tuple[str, str, str]] = [
            (wc, ln, sh)
            for wc in workcenters
            for ln in lines
            for sh in shifts
        ]
        slot_count = len(slots)
        if slot_count <= 0:
            raise to_http_exception(BusinessRuleViolationException("Unable to build schedule slots."))

        planned_total = Decimal(str(supply_plan.planned_prod_qty or 0))
        base_qty = (planned_total / Decimal(slot_count)).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
        assigned_total = base_qty * slot_count
        remainder = (planned_total - assigned_total).quantize(Decimal("0.01"))

        self._repo.delete_by_supply_plan(supply_plan.id)

        shift_offsets = {
            "Shift-A": 6,
            "Shift-B": 14,
            "Shift-C": 22,
        }
        schedule_start_date = datetime.combine(supply_plan.period, datetime.min.time())

        created: list[ProductionSchedule] = []
        for idx, (wc, ln, sh) in enumerate(slots, start=1):
            qty = base_qty
            if remainder > 0:
                add = min(remainder, Decimal("0.01"))
                qty = (qty + add).quantize(Decimal("0.01"))
                remainder = (remainder - add).quantize(Decimal("0.01"))

            start_hour = shift_offsets.get(sh, 6)
            slot_start = schedule_start_date + timedelta(hours=start_hour) + timedelta(days=(idx - 1) // len(shifts))
            slot_end = slot_start + timedelta(hours=body.duration_hours_per_slot)

            row = ProductionSchedule(
                supply_plan_id=supply_plan.id,
                product_id=supply_plan.product_id,
                period=supply_plan.period,
                workcenter=wc,
                line=ln,
                shift=sh,
                sequence_order=idx,
                planned_qty=qty,
                planned_start_at=slot_start,
                planned_end_at=slot_end,
                status="draft",
                created_by=user_id,
            )
            self._db.add(row)
            created.append(row)

        self._db.commit()
        for row in created:
            self._db.refresh(row)
        return created

    def update_schedule_status(
        self,
        schedule_id: int,
        body: ProductionScheduleStatusUpdateRequest,
    ) -> ProductionSchedule:
        row = self._repo.get_by_id(schedule_id)
        if not row:
            raise to_http_exception(EntityNotFoundException("ProductionSchedule", schedule_id))
        allowed = {"draft", "released", "in_progress", "completed"}
        if body.status not in allowed:
            raise to_http_exception(BusinessRuleViolationException(f"Invalid status '{body.status}'"))
        return self._repo.update(row, {"status": body.status})

    def summarize_capacity(self, supply_plan_id: int) -> ProductionCapacitySummaryResponse:
        supply_plan = self._supply_repo.get_by_id(supply_plan_id)
        if not supply_plan:
            raise to_http_exception(EntityNotFoundException("SupplyPlan", supply_plan_id))

        rows = self._repo.list_filtered(supply_plan_id=supply_plan_id)
        planned_total = sum(Decimal(str(r.planned_qty or 0)) for r in rows)
        cap_max = Decimal(str(supply_plan.capacity_max)) if supply_plan.capacity_max is not None else None

        utilization_pct = float((planned_total / cap_max) * 100) if cap_max and cap_max > 0 else 0.0
        overloaded = bool(cap_max is not None and planned_total > cap_max)

        grouped: dict[tuple[str, str, str], Decimal] = {}
        counts: dict[tuple[str, str, str], int] = {}
        for r in rows:
            key = (r.workcenter, r.line, r.shift)
            grouped[key] = grouped.get(key, Decimal("0")) + Decimal(str(r.planned_qty or 0))
            counts[key] = counts.get(key, 0) + 1

        groups = [
            CapacityGroupSummary(
                workcenter=wc,
                line=ln,
                shift=sh,
                slot_count=counts[(wc, ln, sh)],
                total_planned_qty=qty,
            )
            for (wc, ln, sh), qty in sorted(grouped.items(), key=lambda x: (x[0][0], x[0][1], x[0][2]))
        ]

        return ProductionCapacitySummaryResponse(
            supply_plan_id=supply_plan_id,
            slot_count=len(rows),
            planned_total_qty=planned_total,
            capacity_max_qty=cap_max,
            utilization_pct=utilization_pct,
            overloaded=overloaded,
            groups=groups,
        )

    def resequence_schedule(
        self,
        schedule_id: int,
        body: ProductionScheduleResequenceRequest,
    ) -> List[ProductionSchedule]:
        row = self._repo.get_by_id(schedule_id)
        if not row:
            raise to_http_exception(EntityNotFoundException("ProductionSchedule", schedule_id))

        rows = self._repo.list_filtered(supply_plan_id=row.supply_plan_id)
        if len(rows) <= 1:
            return rows

        rows = sorted(rows, key=lambda r: r.sequence_order)
        idx = next((i for i, r in enumerate(rows) if r.id == schedule_id), None)
        if idx is None:
            raise to_http_exception(EntityNotFoundException("ProductionSchedule", schedule_id))

        if body.direction == "up":
            if idx == 0:
                return rows
            swap_idx = idx - 1
        else:
            if idx == len(rows) - 1:
                return rows
            swap_idx = idx + 1

        rows[idx].sequence_order, rows[swap_idx].sequence_order = (
            rows[swap_idx].sequence_order,
            rows[idx].sequence_order,
        )
        self._db.commit()

        reordered = self._repo.list_filtered(supply_plan_id=row.supply_plan_id)
        return sorted(reordered, key=lambda r: r.sequence_order)
