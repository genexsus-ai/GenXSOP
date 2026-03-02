"""
Inventory Service — Service Layer (SRP / DIP)
"""
from datetime import datetime, timedelta
from uuid import uuid4
from math import ceil
from typing import Optional, List, Tuple
import json
import random
from decimal import Decimal, ROUND_CEILING
from statistics import NormalDist
from sqlalchemy.orm import Session

from app.repositories.demand_repository import DemandPlanRepository
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
    InventoryRecommendationApproveRequest,
    InventoryRebalanceRecommendationView,
    InventoryAutoApplyRequest,
    InventoryAutoApplyResponse,
    InventoryControlTowerSummary,
    InventoryDataQualityView,
    InventoryEscalationItem,
    InventoryWorkingCapitalSummary,
    InventoryAssessmentScorecard,
    InventoryAssessmentAreaScore,
    InventoryServiceLevelAnalyticsRequest,
    InventoryServiceLevelAnalyticsResponse,
    InventoryServiceLevelDistributionPoint,
    InventoryServiceLevelSuggestion,
)
from app.core.exceptions import EntityNotFoundException, to_http_exception
from app.utils.events import get_event_bus, EntityUpdatedEvent


class InventoryService:

    def __init__(self, db: Session):
        self._repo = InventoryRepository(db)
        self._exception_repo = InventoryExceptionRepository(db)
        self._demand_repo = DemandPlanRepository(db)
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
            quality = self._compute_data_quality(inv)
            if payload.enforce_quality_gate and quality.overall_score < payload.min_quality_score:
                continue

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
                "quality_score": quality.overall_score,
                "quality_tier": quality.quality_tier,
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
            if self._requires_maker_checker(rec, inv) and rec.status != "accepted":
                raise ValueError(
                    "High-impact policy change requires approval before apply. "
                    "Call recommendation approve endpoint first."
                )
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

    def approve_recommendation(
        self,
        recommendation_id: int,
        payload: InventoryRecommendationApproveRequest,
        user_id: int,
    ) -> InventoryPolicyRecommendationView:
        rec = self._recommendation_repo.get_by_id(recommendation_id)
        if not rec:
            raise to_http_exception(EntityNotFoundException("InventoryPolicyRecommendation", recommendation_id))
        if rec.status in ("rejected", "applied"):
            raise ValueError("Only pending recommendations can be approved.")

        rec = self._recommendation_repo.update(
            rec,
            {
                "status": "accepted",
                "decision_notes": payload.notes or "Approved for application",
                "decided_by": user_id,
                "decided_at": datetime.utcnow(),
            },
        )
        inv = self.get_inventory(rec.inventory_id)
        return self._build_recommendation_view(rec, inv)

    def get_data_quality(
        self,
        product_id: Optional[int] = None,
        location: Optional[str] = None,
    ) -> List[InventoryDataQualityView]:
        scope = self._repo.list_for_policy(product_id=product_id, location=location)
        return [self._compute_data_quality(inv) for inv in scope]

    def get_escalations(self) -> List[InventoryEscalationItem]:
        today = datetime.utcnow().date()
        open_ex = self._exception_repo.list_filtered(status="open")
        in_progress_ex = self._exception_repo.list_filtered(status="in_progress")
        all_ex = open_ex + in_progress_ex
        escalations: List[InventoryEscalationItem] = []

        for ex in all_ex:
            inv = self.get_inventory(ex.inventory_id)
            due = ex.due_date
            overdue_days = (today - due).days if due else 0
            if ex.severity == "high" and (due is None or overdue_days >= 0):
                level = "L2"
                reason = "High-severity exception requires immediate escalation"
            elif overdue_days >= 3:
                level = "L2"
                reason = f"Exception overdue by {overdue_days} days"
            elif overdue_days > 0:
                level = "L1"
                reason = f"Exception overdue by {overdue_days} days"
            else:
                continue

            escalations.append(
                InventoryEscalationItem(
                    exception_id=ex.id,
                    inventory_id=ex.inventory_id,
                    product_id=inv.product_id,
                    location=inv.location,
                    severity=ex.severity,
                    status=ex.status,
                    owner_user_id=ex.owner_user_id,
                    due_date=ex.due_date,
                    escalation_level=level,
                    escalation_reason=reason,
                )
            )
        return escalations

    def get_working_capital_summary(self) -> InventoryWorkingCapitalSummary:
        all_inv = self._repo.get_all_inventory()
        total_value = sum(((inv.valuation or Decimal("0")) for inv in all_inv), Decimal("0"))
        excess_value = sum(((inv.valuation or Decimal("0")) for inv in all_inv if inv.status == "excess"), Decimal("0"))
        low_exposure = sum(((inv.valuation or Decimal("0")) for inv in all_inv if inv.status in ("low", "critical")), Decimal("0"))

        annual_carrying_rate = Decimal("0.18")
        annual_cost = (total_value * annual_carrying_rate).quantize(Decimal("0.01"))
        monthly_cost = (annual_cost / Decimal("12")).quantize(Decimal("0.01"))

        if total_value <= 0:
            health_idx = 100.0
        else:
            risk_ratio = (excess_value + low_exposure) / total_value
            health_idx = float(max(Decimal("0"), Decimal("100") - (risk_ratio * Decimal("100"))).quantize(Decimal("0.1")))

        return InventoryWorkingCapitalSummary(
            total_inventory_value=total_value.quantize(Decimal("0.01")),
            estimated_carrying_cost_annual=annual_cost,
            estimated_carrying_cost_monthly=monthly_cost,
            excess_inventory_value=excess_value.quantize(Decimal("0.01")),
            low_stock_exposure_value=low_exposure.quantize(Decimal("0.01")),
            inventory_health_index=health_idx,
        )

    def get_assessment_scorecard(self) -> InventoryAssessmentScorecard:
        inv = self._repo.get_all_inventory()
        recs_pending = self._recommendation_repo.list_filtered(status="pending")
        recs_applied = self._recommendation_repo.list_filtered(status="applied")
        exceptions_open = self._exception_repo.list_filtered(status="open")
        exceptions_in_progress = self._exception_repo.list_filtered(status="in_progress")
        all_exceptions = exceptions_open + exceptions_in_progress

        checks = {
            "Policy Logic": [
                any((i.safety_stock or Decimal("0")) > 0 for i in inv),
                any((i.reorder_point or Decimal("0")) > 0 for i in inv),
                len({i.status for i in inv}) >= 2,
            ],
            "Forecast Integration": [
                any(r.signals_json and "demand_pressure" in r.signals_json for r in (recs_pending + recs_applied)),
                any(r.signals_json and "quality_score" in r.signals_json for r in (recs_pending + recs_applied)),
                any(r.confidence_score is not None for r in (recs_pending + recs_applied)),
            ],
            "Supply Constraints": [
                any((i.max_stock or Decimal("0")) > 0 for i in inv),
                len(all_exceptions) > 0,
                any(ex.exception_type in ("stockout_risk", "excess_risk") for ex in all_exceptions),
            ],
            "Governance & Cadence": [
                len(all_exceptions) > 0,
                any(r.decided_by is not None for r in (recs_pending + recs_applied)),
                any(r.decision_notes for r in (recs_pending + recs_applied)),
            ],
            "Outcome KPIs": [
                len(recs_applied) > 0,
                any(i.status == "normal" for i in inv),
                any(i.status in ("low", "critical", "excess") for i in inv),
            ],
        }

        def _rag(yes_count: int, total_count: int) -> str:
            ratio = (yes_count / total_count) if total_count else 0
            if ratio >= 0.8:
                return "green"
            if ratio >= 0.4:
                return "amber"
            return "red"

        areas: List[InventoryAssessmentAreaScore] = []
        total_yes = 0
        total_checks = 0

        for area, values in checks.items():
            yes_count = sum(1 for v in values if v)
            total_count = len(values)
            total_yes += yes_count
            total_checks += total_count
            areas.append(
                InventoryAssessmentAreaScore(
                    area=area,
                    yes_count=yes_count,
                    total_count=total_count,
                    score_0_to_3=yes_count,
                    rag=_rag(yes_count, total_count),
                )
            )

        if total_yes <= 5:
            maturity = "Level 1: Transactional / static settings"
        elif total_yes <= 11:
            maturity = "Level 2: Partial optimization"
        else:
            maturity = "Level 3: Mature optimization foundation"

        return InventoryAssessmentScorecard(
            total_yes=total_yes,
            total_checks=total_checks,
            maturity_level=maturity,
            areas=areas,
        )

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
            quality_score = Decimal(str(signals.get("quality_score", 0)))
            if confidence < Decimal(str(payload.min_confidence)):
                continue
            if demand_pressure > Decimal(str(payload.max_demand_pressure)):
                continue
            if quality_score < Decimal(str(payload.min_quality_score)):
                continue
            eligible.append(rec)

        if not payload.dry_run:
            for rec in eligible:
                inv = self.get_inventory(rec.inventory_id)
                if self._requires_maker_checker(rec, inv):
                    # Guardrail: autonomous flow cannot bypass maker-checker.
                    continue
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

    def analyze_service_level_under_uncertainty(
        self,
        payload: InventoryServiceLevelAnalyticsRequest,
    ) -> InventoryServiceLevelAnalyticsResponse:
        inv = self._resolve_inventory_scope(payload)

        demand_mean_daily, demand_std_daily = self._estimate_daily_demand_stats(inv)
        if payload.demand_std_override is not None:
            demand_std_daily = max(Decimal("0.01"), Decimal(str(payload.demand_std_override)))
        lead_time_mean_days, lead_time_std_days = self._estimate_lead_time_stats(inv, payload)

        mean_dlt = demand_mean_daily * lead_time_mean_days
        variance_dlt = (
            (lead_time_mean_days * (demand_std_daily ** 2))
            + ((demand_mean_daily ** 2) * (lead_time_std_days ** 2))
        )
        std_dlt = max(Decimal("0.0001"), Decimal(str(float(variance_dlt) ** 0.5)))

        reorder_point = inv.reorder_point or Decimal("0")
        on_hand = inv.on_hand_qty or Decimal("0")
        safety_stock = inv.safety_stock or Decimal("0")

        if payload.method == "monte_carlo":
            cycle_service_level, expected_shortage_units, fill_rate, distribution = self._run_monte_carlo(
                mean_dlt=mean_dlt,
                std_dlt=std_dlt,
                reorder_point=reorder_point,
                simulation_runs=payload.simulation_runs,
                bucket_count=payload.bucket_count,
            )
        else:
            z_current = float((reorder_point - mean_dlt) / std_dlt)
            normal = NormalDist()
            cycle_service_level = normal.cdf(z_current)
            expected_shortage_units = self._expected_shortage_units(std_dlt, z_current)
            fill_rate = max(0.0, min(1.0, 1.0 - float(expected_shortage_units / max(mean_dlt, Decimal("1")))))
            samples = [
                max(0.0, random.normalvariate(float(mean_dlt), float(std_dlt)))
                for _ in range(min(5000, max(1000, payload.simulation_runs)))
            ]
            distribution = self._build_distribution(samples, payload.bucket_count)

        stockout_probability = max(0.0, min(1.0, 1.0 - cycle_service_level))
        z_target = Decimal(str(self._target_service_to_z(payload.target_service_level)))
        recommended_safety_stock = (z_target * std_dlt).quantize(Decimal("0.01"))
        recommended_reorder_point = (mean_dlt + recommended_safety_stock).quantize(Decimal("0.01"))

        curve_targets = [0.90, 0.95, 0.97, 0.99]
        service_level_curve = []
        for t in curve_targets:
            z = Decimal(str(self._target_service_to_z(t)))
            req_ss = (z * std_dlt).quantize(Decimal("0.01"))
            service_level_curve.append(
                InventoryServiceLevelSuggestion(
                    target_service_level=t,
                    required_safety_stock=req_ss,
                    required_reorder_point=(mean_dlt + req_ss).quantize(Decimal("0.01")),
                )
            )

        return InventoryServiceLevelAnalyticsResponse(
            inventory_id=inv.id,
            product_id=inv.product_id,
            location=inv.location,
            method=payload.method,
            target_service_level=payload.target_service_level,
            current_on_hand_qty=on_hand.quantize(Decimal("0.01")),
            current_safety_stock=safety_stock.quantize(Decimal("0.01")),
            current_reorder_point=reorder_point.quantize(Decimal("0.01")),
            demand_mean_daily=demand_mean_daily.quantize(Decimal("0.0001")),
            demand_std_daily=demand_std_daily.quantize(Decimal("0.0001")),
            lead_time_mean_days=lead_time_mean_days.quantize(Decimal("0.01")),
            lead_time_std_days=lead_time_std_days.quantize(Decimal("0.01")),
            mean_demand_during_lead_time=mean_dlt.quantize(Decimal("0.01")),
            std_demand_during_lead_time=std_dlt.quantize(Decimal("0.01")),
            cycle_service_level=round(cycle_service_level, 4),
            fill_rate=round(fill_rate, 4),
            stockout_probability=round(stockout_probability, 4),
            expected_shortage_units=expected_shortage_units.quantize(Decimal("0.01")),
            recommended_safety_stock=recommended_safety_stock,
            recommended_reorder_point=recommended_reorder_point,
            service_level_curve=service_level_curve,
            distribution=distribution,
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

    def _resolve_inventory_scope(self, payload: InventoryServiceLevelAnalyticsRequest) -> Inventory:
        if payload.inventory_id:
            return self.get_inventory(payload.inventory_id)

        if payload.product_id and payload.location:
            inv = self._repo.get_by_product_and_location(payload.product_id, payload.location)
            if inv:
                return inv

        if payload.product_id:
            invs = self._repo.list_for_policy(product_id=payload.product_id, location=payload.location)
            if invs:
                return invs[0]

        raise ValueError("Provide inventory_id or valid product_id/location scope for service-level analytics")

    def _estimate_daily_demand_stats(self, inv: Inventory) -> Tuple[Decimal, Decimal]:
        history = self._demand_repo.get_with_actuals(inv.product_id)
        actuals = [Decimal(str(h.actual_qty)) for h in history[-12:] if h.actual_qty is not None]

        if not actuals:
            basis = (inv.allocated_qty or Decimal("0")) + (inv.in_transit_qty or Decimal("0"))
            mean = max(Decimal("1"), basis / Decimal("30"))
            return mean, max(Decimal("0.25"), mean * Decimal("0.25"))

        daily = [a / Decimal("30") for a in actuals]
        mean = sum(daily, Decimal("0")) / Decimal(str(len(daily)))
        if len(daily) == 1:
            std = max(Decimal("0.25"), mean * Decimal("0.20"))
        else:
            var = sum(((d - mean) ** 2 for d in daily), Decimal("0")) / Decimal(str(len(daily) - 1))
            std = Decimal(str(float(var) ** 0.5))

        return max(Decimal("0.01"), mean), max(Decimal("0.01"), std)

    def _estimate_lead_time_stats(
        self,
        inv: Inventory,
        payload: InventoryServiceLevelAnalyticsRequest,
    ) -> Tuple[Decimal, Decimal]:
        product = self._product_repo.get_by_id(inv.product_id)
        supply = self._supply_repo.get_latest_by_product(inv.product_id)

        base = Decimal("14")
        if product and getattr(product, "lead_time_days", None):
            base = Decimal(str(product.lead_time_days))
        if supply and getattr(supply, "lead_time_days", None):
            base = Decimal(str(supply.lead_time_days))

        std = Decimal(str(payload.lead_time_std_override)) if payload.lead_time_std_override is not None else max(Decimal("0.5"), base * Decimal("0.15"))
        return max(Decimal("1"), base), max(Decimal("0.01"), std)

    def _target_service_to_z(self, service_level: float) -> float:
        # Clamp to avoid +/- inf.
        bounded = min(0.999, max(0.5001, service_level))
        return NormalDist().inv_cdf(bounded)

    def _expected_shortage_units(self, std_dlt: Decimal, z: float) -> Decimal:
        normal = NormalDist()
        phi = Decimal(str(normal.pdf(z)))
        tail = Decimal(str(1 - normal.cdf(z)))
        loss = phi - (Decimal(str(z)) * tail)
        return max(Decimal("0"), std_dlt * max(Decimal("0"), loss))

    def _run_monte_carlo(
        self,
        mean_dlt: Decimal,
        std_dlt: Decimal,
        reorder_point: Decimal,
        simulation_runs: int,
        bucket_count: int,
    ) -> Tuple[float, Decimal, float, List[InventoryServiceLevelDistributionPoint]]:
        samples = [
            max(0.0, random.normalvariate(float(mean_dlt), float(std_dlt)))
            for _ in range(simulation_runs)
        ]

        no_stockout = sum(1 for d in samples if d <= float(reorder_point))
        cycle_service_level = (no_stockout / max(1, simulation_runs))
        shortages = [max(0.0, d - float(reorder_point)) for d in samples]
        expected_shortage = Decimal(str(sum(shortages) / max(1, len(shortages))))
        avg_demand = max(1.0, sum(samples) / max(1, len(samples)))
        fill_rate = max(0.0, min(1.0, 1.0 - (float(expected_shortage) / avg_demand)))

        distribution = self._build_distribution(samples, bucket_count)
        return cycle_service_level, expected_shortage, fill_rate, distribution

    def _build_distribution(self, samples: List[float], bucket_count: int) -> List[InventoryServiceLevelDistributionPoint]:
        if not samples:
            return []

        lo = min(samples)
        hi = max(samples)
        if hi <= lo:
            hi = lo + 1.0
        width = (hi - lo) / bucket_count
        bins = [0 for _ in range(bucket_count)]

        for s in samples:
            idx = int((s - lo) / width) if width > 0 else 0
            idx = max(0, min(bucket_count - 1, idx))
            bins[idx] += 1

        total = len(samples)
        points: List[InventoryServiceLevelDistributionPoint] = []
        for i, c in enumerate(bins):
            start = lo + i * width
            end = start + width
            midpoint = (start + end) / 2
            points.append(
                InventoryServiceLevelDistributionPoint(
                    bucket=f"{start:.1f}-{end:.1f}",
                    midpoint=round(midpoint, 3),
                    probability=round(c / total, 6),
                )
            )
        return points

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

    def _compute_data_quality(self, inv: Inventory) -> InventoryDataQualityView:
        completeness_points = 0
        if inv.on_hand_qty is not None:
            completeness_points += 1
        if inv.safety_stock is not None:
            completeness_points += 1
        if inv.reorder_point is not None:
            completeness_points += 1
        if inv.max_stock is not None:
            completeness_points += 1
        if inv.valuation is not None:
            completeness_points += 1
        completeness_score = round(completeness_points / 5, 4)

        freshness_score = 1.0
        if inv.updated_at:
            age_hours = (datetime.utcnow() - inv.updated_at).total_seconds() / 3600
            if age_hours > 168:
                freshness_score = 0.5
            elif age_hours > 72:
                freshness_score = 0.75

        consistency_score = 1.0
        if (inv.on_hand_qty or Decimal("0")) < Decimal("0"):
            consistency_score = 0.0
        elif inv.max_stock and inv.reorder_point and inv.max_stock < inv.reorder_point:
            consistency_score = 0.5

        overall = round((0.4 * completeness_score) + (0.3 * freshness_score) + (0.3 * consistency_score), 4)
        tier = "high" if overall >= 0.85 else "medium" if overall >= 0.60 else "low"
        return InventoryDataQualityView(
            inventory_id=inv.id,
            product_id=inv.product_id,
            location=inv.location,
            completeness_score=completeness_score,
            freshness_score=round(freshness_score, 4),
            consistency_score=round(consistency_score, 4),
            overall_score=overall,
            quality_tier=tier,
        )

    def _requires_maker_checker(self, rec, inv: Inventory) -> bool:
        base = inv.reorder_point or Decimal("1")
        if base <= 0:
            return False
        delta = abs((rec.recommended_reorder_point or Decimal("0")) - base)
        pct = delta / base
        return pct >= Decimal("0.20")

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
