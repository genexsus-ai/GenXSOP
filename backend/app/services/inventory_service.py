"""
Inventory Service — Service Layer (SRP / DIP)
"""
from datetime import datetime, timedelta
from uuid import uuid4
from math import ceil
from typing import Optional, List
import json
from decimal import Decimal, ROUND_CEILING
from sqlalchemy.orm import Session

from app.repositories.inventory_repository import InventoryRepository
from app.repositories.inventory_exception_repository import InventoryExceptionRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.supply_repository import SupplyPlanRepository
from app.repositories.inventory_recommendation_repository import InventoryRecommendationRepository
from app.models.inventory import Inventory
from app.schemas.inventory import (
    InventoryUpdate,
    InventoryListResponse,
    InventoryHealthSummary,
    InventoryOptimizationRunRequest,
    InventoryOptimizationRunResponse,
    InventoryPolicyOverride,
    InventoryExceptionView,
    InventoryExceptionUpdateRequest,
    InventoryRecommendationGenerateRequest,
    InventoryPolicyRecommendationView,
    InventoryRecommendationDecisionRequest,
    InventoryRebalanceRecommendationView,
    InventoryAutoApplyRequest,
    InventoryAutoApplyResponse,
    InventoryControlTowerSummary,
)
from app.core.exceptions import EntityNotFoundException, to_http_exception
from app.utils.events import get_event_bus, EntityUpdatedEvent


class InventoryService:

    def __init__(self, db: Session):
        self._repo = InventoryRepository(db)
        self._exception_repo = InventoryExceptionRepository(db)
        self._product_repo = ProductRepository(db)
        self._supply_repo = SupplyPlanRepository(db)
        self._recommendation_repo = InventoryRecommendationRepository(db)
        self._bus = get_event_bus()

    def list_inventory(self, page: int = 1, page_size: int = 20, **filters) -> InventoryListResponse:
        items, total = self._repo.list_paginated(page=page, page_size=page_size, **filters)
        return InventoryListResponse(
            items=items, total=total, page=page, page_size=page_size,
            total_pages=ceil(total / page_size) if total else 0,
        )

    def get_inventory(self, inventory_id: int) -> Inventory:
        inv = self._repo.get_by_id(inventory_id)
        if not inv:
            raise to_http_exception(EntityNotFoundException("Inventory", inventory_id))
        return inv

    def update_inventory(self, inventory_id: int, data: InventoryUpdate, user_id: int) -> Inventory:
        inv = self.get_inventory(inventory_id)
        updates = data.model_dump(exclude_unset=True)
        old_values = {
            "on_hand_qty": self._serialize(inv.on_hand_qty),
            "allocated_qty": self._serialize(inv.allocated_qty),
            "in_transit_qty": self._serialize(inv.in_transit_qty),
            "safety_stock": self._serialize(inv.safety_stock),
            "reorder_point": self._serialize(inv.reorder_point),
            "max_stock": self._serialize(inv.max_stock),
        }
        result = self._repo.update(inv, updates)
        # Recalculate status based on new quantities
        result = self._recalculate_status(result)
        self._bus.publish(EntityUpdatedEvent(
            entity_type="inventory",
            entity_id=inventory_id,
            user_id=user_id,
            old_values=old_values,
            new_values={k: self._serialize(v) for k, v in updates.items()},
        ))
        return result

    def run_optimization(
        self,
        payload: InventoryOptimizationRunRequest,
        user_id: int,
    ) -> InventoryOptimizationRunResponse:
        scope = self._repo.list_for_policy(product_id=payload.product_id, location=payload.location)
        run_id = str(uuid4())
        exceptions: List[InventoryExceptionView] = []
        updated = 0

        for inv in scope:
            old_values = {
                "safety_stock": self._serialize(inv.safety_stock),
                "reorder_point": self._serialize(inv.reorder_point),
                "max_stock": self._serialize(inv.max_stock),
                "status": inv.status,
            }

            demand_basis = (inv.allocated_qty or Decimal("0")) + (inv.in_transit_qty or Decimal("0"))
            review_days = max(1, payload.review_period_days)
            daily_demand = max(demand_basis / Decimal(str(review_days)), Decimal("1"))
            z_factor = self._service_level_to_z(payload.service_level_target)
            lead_time_days = self._resolve_effective_lead_time_days(inv, payload)
            lead_time = Decimal(str(lead_time_days))

            safety_stock = (daily_demand * Decimal(str(z_factor)) * lead_time.sqrt()).quantize(Decimal("0.01"))
            reorder_point = (daily_demand * lead_time + safety_stock).quantize(Decimal("0.01"))
            target_max = (reorder_point * Decimal("1.50")).quantize(Decimal("0.01"))

            # Constraint-aware policy shaping
            if payload.moq_units and payload.moq_units > 0:
                reorder_point = max(reorder_point, payload.moq_units)
            if payload.lot_size_units and payload.lot_size_units > 0:
                reorder_point = self._round_up_to_lot(reorder_point, payload.lot_size_units)
                target_max = self._round_up_to_lot(target_max, payload.lot_size_units)
            if payload.capacity_max_units and payload.capacity_max_units > 0:
                target_max = min(target_max, payload.capacity_max_units)
                reorder_point = min(reorder_point, target_max)

            inv = self._repo.update(
                inv,
                {
                    "safety_stock": safety_stock,
                    "reorder_point": reorder_point,
                    "max_stock": target_max,
                },
            )
            inv = self._recalculate_status(inv)
            updated += 1

            new_values = {
                "safety_stock": str(safety_stock),
                "reorder_point": str(reorder_point),
                "max_stock": str(target_max),
                "status": inv.status,
                "policy_source": "system",
                "run_id": run_id,
            }
            self._bus.publish(
                EntityUpdatedEvent(
                    entity_type="inventory_policy",
                    entity_id=inv.id,
                    user_id=user_id,
                    old_values=old_values,
                    new_values=new_values,
                )
            )

            exceptions.extend(self._build_exceptions_for_inventory(inv, upsert=True))

        return InventoryOptimizationRunResponse(
            run_id=run_id,
            processed_count=len(scope),
            updated_count=updated,
            exception_count=len(exceptions),
            generated_at=datetime.utcnow(),
            exceptions=exceptions,
        )

    def apply_policy_override(
        self,
        inventory_id: int,
        payload: InventoryPolicyOverride,
        user_id: int,
    ) -> Inventory:
        inv = self.get_inventory(inventory_id)
        updates = payload.model_dump(exclude_unset=True)
        reason = updates.pop("reason", "manual override")

        old_values = {
            "safety_stock": self._serialize(inv.safety_stock),
            "reorder_point": self._serialize(inv.reorder_point),
            "max_stock": self._serialize(inv.max_stock),
            "status": inv.status,
        }

        inv = self._repo.update(inv, updates)
        inv = self._recalculate_status(inv)

        self._bus.publish(
            EntityUpdatedEvent(
                entity_type="inventory_policy_override",
                entity_id=inv.id,
                user_id=user_id,
                old_values=old_values,
                new_values={
                    **{k: self._serialize(v) for k, v in updates.items()},
                    "reason": reason,
                    "status": inv.status,
                },
            )
        )
        return inv

    def get_policy_exceptions(
        self,
        product_id: Optional[int] = None,
        location: Optional[str] = None,
        status: Optional[str] = None,
        owner_user_id: Optional[int] = None,
    ) -> List[InventoryExceptionView]:
        persisted = self._exception_repo.list_filtered(status=status, owner_user_id=owner_user_id)
        if persisted:
            inv_scope = {i.id: i for i in self._repo.list_for_policy(product_id=product_id, location=location)}
            return [
                InventoryExceptionView(
                    id=ex.id,
                    inventory_id=ex.inventory_id,
                    product_id=inv_scope[ex.inventory_id].product_id,
                    location=inv_scope[ex.inventory_id].location,
                    exception_type=ex.exception_type,
                    severity=ex.severity,
                    status=ex.status,
                    recommended_action=ex.recommended_action,
                    owner_user_id=ex.owner_user_id,
                    due_date=ex.due_date,
                    notes=ex.notes,
                )
                for ex in persisted
                if ex.inventory_id in inv_scope
            ]

        scope = self._repo.list_for_policy(product_id=product_id, location=location)
        exceptions: List[InventoryExceptionView] = []
        for inv in scope:
            exceptions.extend(self._build_exceptions_for_inventory(inv, upsert=False))
        return exceptions

    def update_exception(
        self,
        exception_id: int,
        payload: InventoryExceptionUpdateRequest,
        user_id: int,
    ) -> InventoryExceptionView:
        ex = self._exception_repo.get_by_id(exception_id)
        if not ex:
            raise to_http_exception(EntityNotFoundException("InventoryPolicyException", exception_id))

        updates = payload.model_dump(exclude_unset=True)
        old_values = {
            "status": ex.status,
            "owner_user_id": ex.owner_user_id,
            "due_date": ex.due_date.isoformat() if ex.due_date else None,
            "notes": ex.notes,
        }
        ex = self._exception_repo.update(ex, updates)

        self._bus.publish(
            EntityUpdatedEvent(
                entity_type="inventory_policy_exception",
                entity_id=exception_id,
                user_id=user_id,
                old_values=old_values,
                new_values={
                    "status": ex.status,
                    "owner_user_id": ex.owner_user_id,
                    "due_date": ex.due_date.isoformat() if ex.due_date else None,
                    "notes": ex.notes,
                },
            )
        )

        inv = self.get_inventory(ex.inventory_id)
        return InventoryExceptionView(
            id=ex.id,
            inventory_id=ex.inventory_id,
            product_id=inv.product_id,
            location=inv.location,
            exception_type=ex.exception_type,
            severity=ex.severity,
            status=ex.status,
            recommended_action=ex.recommended_action,
            owner_user_id=ex.owner_user_id,
            due_date=ex.due_date,
            notes=ex.notes,
        )

    def generate_recommendations(
        self,
        payload: InventoryRecommendationGenerateRequest,
        user_id: int,
    ) -> List[InventoryPolicyRecommendationView]:
        scope = self._repo.list_for_policy(product_id=payload.product_id, location=payload.location)
        recommendations: List[InventoryPolicyRecommendationView] = []

        for inv in scope[: payload.max_items]:
            on_hand = inv.on_hand_qty or Decimal("0")
            allocated = inv.allocated_qty or Decimal("0")
            in_transit = inv.in_transit_qty or Decimal("0")

            demand_pressure = (allocated + in_transit) / max(on_hand, Decimal("1"))
            risk_boost = Decimal("0.10") if inv.status in ("critical", "low") else Decimal("0")
            pressure_boost = min(Decimal("0.30"), demand_pressure * Decimal("0.20"))
            multiplier = Decimal("1.05") + risk_boost + pressure_boost

            rec_ss = max((inv.safety_stock or Decimal("0")) * multiplier, Decimal("1")).quantize(Decimal("0.01"))
            rec_rop = max((inv.reorder_point or Decimal("0")) * multiplier, rec_ss * Decimal("1.25")).quantize(Decimal("0.01"))
            rec_max = max((inv.max_stock or Decimal("0")) * multiplier, rec_rop * Decimal("1.40")).quantize(Decimal("0.01"))

            lead_time_days = self._resolve_effective_lead_time_days(
                inv,
                payload=type("_P", (), {
                    "lead_time_days": 14,
                    "lead_time_variability_days": Decimal("0"),
                })(),
            )
            confidence = self._recommendation_confidence(inv, demand_pressure, lead_time_days)
            if confidence < Decimal(str(payload.min_confidence)):
                continue

            signals = {
                "demand_pressure": float(demand_pressure),
                "inventory_status": inv.status,
                "lead_time_days": float(lead_time_days),
                "on_hand_qty": float(on_hand),
                "allocated_qty": float(allocated),
                "in_transit_qty": float(in_transit),
            }
            rationale = (
                f"AI tuning detected demand pressure {float(demand_pressure):.2f} with status '{inv.status}'. "
                "Recommended policy uplift to improve service and reduce stockout risk."
            )

            pending = self._recommendation_repo.get_latest_pending_by_inventory(inv.id)
            if pending:
                pending = self._recommendation_repo.update(
                    pending,
                    {
                        "recommended_safety_stock": rec_ss,
                        "recommended_reorder_point": rec_rop,
                        "recommended_max_stock": rec_max,
                        "confidence_score": confidence,
                        "rationale": rationale,
                        "signals_json": json.dumps(signals),
                    },
                )
                rec = pending
            else:
                rec = self._recommendation_repo.create(
                    self._recommendation_repo.model(
                        inventory_id=inv.id,
                        recommended_safety_stock=rec_ss,
                        recommended_reorder_point=rec_rop,
                        recommended_max_stock=rec_max,
                        confidence_score=confidence,
                        rationale=rationale,
                        signals_json=json.dumps(signals),
                        status="pending",
                    )
                )

            self._bus.publish(
                EntityUpdatedEvent(
                    entity_type="inventory_policy_recommendation",
                    entity_id=rec.id,
                    user_id=user_id,
                    new_values={
                        "status": rec.status,
                        "confidence_score": str(rec.confidence_score),
                        "inventory_id": rec.inventory_id,
                    },
                )
            )

            recommendations.append(self._build_recommendation_view(rec, inv))

        return recommendations

    def list_recommendations(
        self,
        status: Optional[str] = None,
        inventory_id: Optional[int] = None,
        product_id: Optional[int] = None,
        location: Optional[str] = None,
    ) -> List[InventoryPolicyRecommendationView]:
        recs = self._recommendation_repo.list_filtered(status=status, inventory_id=inventory_id)
        inv_scope = {
            inv.id: inv
            for inv in self._repo.list_for_policy(product_id=product_id, location=location)
        }
        return [self._build_recommendation_view(r, inv_scope[r.inventory_id]) for r in recs if r.inventory_id in inv_scope]

    def decide_recommendation(
        self,
        recommendation_id: int,
        payload: InventoryRecommendationDecisionRequest,
        user_id: int,
    ) -> InventoryPolicyRecommendationView:
        rec = self._recommendation_repo.get_by_id(recommendation_id)
        if not rec:
            raise to_http_exception(EntityNotFoundException("InventoryPolicyRecommendation", recommendation_id))

        updates = {
            "status": payload.decision,
            "decision_notes": payload.notes,
            "decided_by": user_id,
            "decided_at": datetime.utcnow(),
        }

        inv = self.get_inventory(rec.inventory_id)
        if payload.decision == "accepted" and payload.apply_changes:
            inv = self._repo.update(
                inv,
                {
                    "safety_stock": rec.recommended_safety_stock,
                    "reorder_point": rec.recommended_reorder_point,
                    "max_stock": rec.recommended_max_stock,
                },
            )
            inv = self._recalculate_status(inv)
            updates["status"] = "applied"

        rec = self._recommendation_repo.update(rec, updates)
        self._bus.publish(
            EntityUpdatedEvent(
                entity_type="inventory_policy_recommendation",
                entity_id=recommendation_id,
                user_id=user_id,
                new_values={
                    "status": rec.status,
                    "decision_notes": rec.decision_notes,
                    "decided_by": rec.decided_by,
                },
            )
        )
        return self._build_recommendation_view(rec, inv)

    def get_rebalance_recommendations(
        self,
        product_id: Optional[int] = None,
        min_transfer_qty: Decimal = Decimal("1"),
    ) -> List[InventoryRebalanceRecommendationView]:
        scope = self._repo.list_for_policy(product_id=product_id)
        grouped = {}
        for inv in scope:
            grouped.setdefault(inv.product_id, []).append(inv)

        recommendations: List[InventoryRebalanceRecommendationView] = []
        for pid, rows in grouped.items():
            lows = [r for r in rows if r.status in ("critical", "low")]
            excesses = [r for r in rows if r.status == "excess"]
            if not lows or not excesses:
                continue

            product = self._product_repo.get_by_id(pid)
            for low in lows:
                required = max(
                    Decimal("0"),
                    (low.reorder_point or Decimal("0")) - (low.on_hand_qty or Decimal("0")),
                )
                if required < min_transfer_qty:
                    continue

                donor = max(
                    excesses,
                    key=lambda e: (e.on_hand_qty or Decimal("0")) - (e.max_stock or Decimal("0")),
                )
                donor_excess = max(
                    Decimal("0"),
                    (donor.on_hand_qty or Decimal("0")) - (donor.max_stock or Decimal("0")),
                )
                transfer_qty = min(required, donor_excess)
                if transfer_qty < min_transfer_qty:
                    continue

                base_service = Decimal("60") if low.status == "critical" else Decimal("75")
                uplift = min(Decimal("25"), (transfer_qty / max(required, Decimal("1"))) * Decimal("20"))

                recommendations.append(
                    InventoryRebalanceRecommendationView(
                        product_id=pid,
                        product_name=getattr(product, "name", None),
                        from_inventory_id=donor.id,
                        from_location=donor.location,
                        to_inventory_id=low.id,
                        to_location=low.location,
                        transfer_qty=transfer_qty.quantize(Decimal("0.01")),
                        estimated_service_uplift_pct=float((base_service + uplift).quantize(Decimal("0.01"))),
                    )
                )
        return recommendations

    def auto_apply_recommendations(
        self,
        payload: InventoryAutoApplyRequest,
        user_id: int,
    ) -> InventoryAutoApplyResponse:
        pending = self._recommendation_repo.list_filtered(status="pending")
        eligible = []
        applied_ids: List[int] = []

        for rec in pending[: payload.max_items]:
            signals = {}
            if rec.signals_json:
                try:
                    signals = json.loads(rec.signals_json)
                except Exception:
                    signals = {}
            demand_pressure = Decimal(str(signals.get("demand_pressure", 0)))
            confidence = Decimal(str(rec.confidence_score or 0))
            if confidence < Decimal(str(payload.min_confidence)):
                continue
            if demand_pressure > Decimal(str(payload.max_demand_pressure)):
                continue
            eligible.append(rec)

        if not payload.dry_run:
            for rec in eligible:
                view = self.decide_recommendation(
                    rec.id,
                    InventoryRecommendationDecisionRequest(
                        decision="accepted",
                        apply_changes=True,
                        notes="Autonomous apply (Phase 5 guardrail policy)",
                    ),
                    user_id=user_id,
                )
                if view.status == "applied":
                    applied_ids.append(view.id)

        return InventoryAutoApplyResponse(
            eligible_count=len(eligible),
            applied_count=0 if payload.dry_run else len(applied_ids),
            skipped_count=max(0, len(pending[: payload.max_items]) - len(eligible)),
            recommendation_ids=applied_ids,
        )

    def get_control_tower_summary(self) -> InventoryControlTowerSummary:
        pending = self._recommendation_repo.list_filtered(status="pending")
        accepted = self._recommendation_repo.list_filtered(status="accepted")
        applied = self._recommendation_repo.list_filtered(status="applied")
        rejected = self._recommendation_repo.list_filtered(status="rejected")

        total_decided = len(accepted) + len(applied) + len(rejected)
        acceptance_rate = 0.0
        if total_decided > 0:
            acceptance_rate = round(((len(accepted) + len(applied)) / total_decided) * 100, 1)

        now = datetime.utcnow().date()
        open_ex = self._exception_repo.list_filtered(status="open")
        in_progress_ex = self._exception_repo.list_filtered(status="in_progress")
        open_total = len(open_ex) + len(in_progress_ex)
        overdue = [
            ex for ex in (open_ex + in_progress_ex)
            if ex.due_date is not None and ex.due_date < now
        ]

        autonomous_24h = len([
            rec for rec in applied
            if rec.decision_notes and "Autonomous apply" in rec.decision_notes
            and rec.decided_at and (datetime.utcnow() - rec.decided_at).total_seconds() <= 86400
        ])

        if len(pending) > 50 or len(overdue) > 20:
            backlog_risk = "high"
        elif len(pending) > 20 or len(overdue) > 5:
            backlog_risk = "medium"
        else:
            backlog_risk = "low"

        return InventoryControlTowerSummary(
            pending_recommendations=len(pending),
            accepted_recommendations=len(accepted),
            applied_recommendations=len(applied),
            acceptance_rate_pct=acceptance_rate,
            autonomous_applied_24h=autonomous_24h,
            open_exceptions=open_total,
            overdue_exceptions=len(overdue),
            recommendation_backlog_risk=backlog_risk,
        )

    def get_health_summary(self) -> InventoryHealthSummary:
        all_inv = self._repo.get_all_inventory()
        total = len(all_inv)
        if total == 0:
            return InventoryHealthSummary(
                total_products=0, normal_count=0, low_count=0, critical_count=0, excess_count=0,
                total_value=Decimal("0"), normal_pct=0.0, low_pct=0.0, critical_pct=0.0, excess_pct=0.0,
            )
        counts = {"normal": 0, "low": 0, "critical": 0, "excess": 0}
        total_value = Decimal("0")
        for inv in all_inv:
            counts[inv.status] = counts.get(inv.status, 0) + 1
            total_value += inv.valuation or Decimal("0")
        return InventoryHealthSummary(
            total_products=total,
            normal_count=counts["normal"],
            low_count=counts["low"],
            critical_count=counts["critical"],
            excess_count=counts["excess"],
            total_value=total_value,
            normal_pct=round(counts["normal"] / total * 100, 1),
            low_pct=round(counts["low"] / total * 100, 1),
            critical_pct=round(counts["critical"] / total * 100, 1),
            excess_pct=round(counts["excess"] / total * 100, 1),
        )

    def get_alerts(self) -> dict:
        return {
            "critical": [
                {"id": i.id, "product_id": i.product_id, "location": i.location, "on_hand_qty": float(i.on_hand_qty)}
                for i in self._repo.get_critical()
            ],
            "low": [
                {"id": i.id, "product_id": i.product_id, "location": i.location, "on_hand_qty": float(i.on_hand_qty)}
                for i in self._repo.get_low()
            ],
            "excess": [
                {"id": i.id, "product_id": i.product_id, "location": i.location, "on_hand_qty": float(i.on_hand_qty)}
                for i in self._repo.get_excess()
            ],
        }

    def _recalculate_status(self, inv: Inventory) -> Inventory:
        """Business rule: recalculate inventory status based on thresholds."""
        on_hand = inv.on_hand_qty or Decimal("0")
        safety = inv.safety_stock or Decimal("0")
        reorder = inv.reorder_point or Decimal("0")
        max_stock = inv.max_stock
        if on_hand < reorder:
            new_status = "critical"
        elif on_hand < safety:
            new_status = "low"
        elif max_stock and on_hand > max_stock:
            new_status = "excess"
        else:
            new_status = "normal"
        return self._repo.update(inv, {"status": new_status})

    def _service_level_to_z(self, service_level_target: float) -> float:
        if service_level_target >= 0.99:
            return 2.33
        if service_level_target >= 0.98:
            return 2.05
        if service_level_target >= 0.95:
            return 1.65
        if service_level_target >= 0.90:
            return 1.28
        return 0.84

    def _build_exceptions_for_inventory(self, inv: Inventory, upsert: bool = False) -> List[InventoryExceptionView]:
        exceptions: List[InventoryExceptionView] = []
        on_hand = inv.on_hand_qty or Decimal("0")
        reorder = inv.reorder_point or Decimal("0")
        max_stock = inv.max_stock or Decimal("0")

        if reorder > 0 and on_hand < reorder:
            severity = "high" if on_hand <= (inv.safety_stock or Decimal("0")) else "medium"
            exceptions.append(
                self._to_exception_view(
                    inv,
                    exception_type="stockout_risk",
                    severity=severity,
                    recommended_action="Advance replenishment or increase planned supply",
                    upsert=upsert,
                )
            )

        if max_stock > 0 and on_hand > max_stock:
            exceptions.append(
                self._to_exception_view(
                    inv,
                    exception_type="excess_risk",
                    severity="medium",
                    recommended_action="Throttle replenishment or rebalance stock across locations",
                    upsert=upsert,
                )
            )

        return exceptions

    def _to_exception_view(
        self,
        inv: Inventory,
        exception_type: str,
        severity: str,
        recommended_action: str,
        upsert: bool,
    ) -> InventoryExceptionView:
        if upsert:
            existing = self._exception_repo.get_open_by_inventory_and_type(inv.id, exception_type)
            if existing:
                existing = self._exception_repo.update(
                    existing,
                    {
                        "severity": severity,
                        "recommended_action": recommended_action,
                        "status": "open" if existing.status == "dismissed" else existing.status,
                    },
                )
            else:
                default_due = datetime.utcnow().date() + timedelta(days=2 if severity == "high" else 5)
                existing = self._exception_repo.create(
                    self._exception_repo.model(
                        inventory_id=inv.id,
                        exception_type=exception_type,
                        severity=severity,
                        status="open",
                        recommended_action=recommended_action,
                        due_date=default_due,
                    )
                )
            return InventoryExceptionView(
                id=existing.id,
                inventory_id=inv.id,
                product_id=inv.product_id,
                location=inv.location,
                exception_type=existing.exception_type,
                severity=existing.severity,
                status=existing.status,
                recommended_action=existing.recommended_action,
                owner_user_id=existing.owner_user_id,
                due_date=existing.due_date,
                notes=existing.notes,
            )

        return InventoryExceptionView(
            inventory_id=inv.id,
            product_id=inv.product_id,
            location=inv.location,
            exception_type=exception_type,
            severity=severity,
            status="open",
            recommended_action=recommended_action,
        )

    def _resolve_effective_lead_time_days(self, inv: Inventory, payload: InventoryOptimizationRunRequest) -> Decimal:
        product = self._product_repo.get_by_id(inv.product_id)
        base = Decimal(str(payload.lead_time_days))
        if product and getattr(product, "lead_time_days", None):
            base = Decimal(str(product.lead_time_days))
        supply = self._supply_repo.get_latest_by_product(inv.product_id)
        if supply and getattr(supply, "lead_time_days", None):
            base = Decimal(str(supply.lead_time_days))
        variability = Decimal(str(payload.lead_time_variability_days or 0))
        return max(Decimal("1"), base + variability)

    def _round_up_to_lot(self, value: Decimal, lot: Decimal) -> Decimal:
        if lot <= 0:
            return value
        multiplier = (value / lot).to_integral_value(rounding=ROUND_CEILING)
        return (multiplier * lot).quantize(Decimal("0.01"))

    def _recommendation_confidence(
        self,
        inv: Inventory,
        demand_pressure: Decimal,
        lead_time_days: Decimal,
    ) -> Decimal:
        base = Decimal("0.72")
        status_adj = Decimal("0.08") if inv.status in ("critical", "low") else Decimal("0")
        pressure_adj = min(Decimal("0.12"), demand_pressure * Decimal("0.10"))
        lead_time_adj = Decimal("0.05") if lead_time_days > Decimal("20") else Decimal("0")
        score = base + status_adj + pressure_adj - lead_time_adj
        return min(Decimal("0.95"), max(Decimal("0.40"), score)).quantize(Decimal("0.0001"))

    def _build_recommendation_view(self, rec, inv: Inventory) -> InventoryPolicyRecommendationView:
        signals = None
        if rec.signals_json:
            try:
                signals = json.loads(rec.signals_json)
            except Exception:
                signals = None

        return InventoryPolicyRecommendationView(
            id=rec.id,
            inventory_id=rec.inventory_id,
            product_id=inv.product_id,
            location=inv.location,
            recommended_safety_stock=rec.recommended_safety_stock,
            recommended_reorder_point=rec.recommended_reorder_point,
            recommended_max_stock=rec.recommended_max_stock,
            confidence_score=rec.confidence_score,
            rationale=rec.rationale,
            signals=signals,
            status=rec.status,
            decision_notes=rec.decision_notes,
            decided_by=rec.decided_by,
            decided_at=rec.decided_at,
            created_at=rec.created_at,
            updated_at=rec.updated_at,
        )

    def _serialize(self, value):
        if isinstance(value, Decimal):
            return str(value)
        return value
