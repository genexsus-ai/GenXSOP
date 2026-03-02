"""
Scenario Service — Service Layer (SRP / DIP)
"""
import json
from math import ceil
from typing import List, Dict, Optional
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Session

from app.repositories.scenario_repository import ScenarioRepository
from app.repositories.demand_repository import DemandPlanRepository
from app.repositories.supply_repository import SupplyPlanRepository
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.inventory_exception_repository import InventoryExceptionRepository
from app.repositories.product_repository import ProductRepository
from app.models.demand_plan import DemandPlan
from app.models.scenario import Scenario
from app.schemas.scenario import ScenarioCreate, ScenarioUpdate, ScenarioListResponse
from app.core.exceptions import EntityNotFoundException, to_http_exception
from app.utils.events import get_event_bus, EntityCreatedEvent, EntityUpdatedEvent, EntityDeletedEvent, PlanStatusChangedEvent


class ScenarioService:

    def __init__(self, db: Session):
        self._db = db
        self._repo = ScenarioRepository(db)
        self._demand_repo = DemandPlanRepository(db)
        self._supply_repo = SupplyPlanRepository(db)
        self._inventory_repo = InventoryRepository(db)
        self._inventory_exception_repo = InventoryExceptionRepository(db)
        self._product_repo = ProductRepository(db)
        self._bus = get_event_bus()

    @staticmethod
    def _to_decimal(value, default: Decimal = Decimal("0")) -> Decimal:
        if value is None:
            return default
        try:
            return Decimal(str(value))
        except Exception:
            return default

    @staticmethod
    def _parse_date(value) -> Optional[date]:
        if not value:
            return None
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                return None
        return None

    def _latest_demand_period(self) -> Optional[date]:
        return self._db.query(DemandPlan.period).order_by(DemandPlan.period.desc()).limit(1).scalar()

    def list_scenarios(self, page: int = 1, page_size: int = 20) -> ScenarioListResponse:
        items, total = self._repo.list_paginated(page=page, page_size=page_size)
        return ScenarioListResponse(
            items=items, total=total, page=page, page_size=page_size,
            total_pages=ceil(total / page_size) if total else 0,
        )

    def get_scenario(self, scenario_id: int) -> Scenario:
        s = self._repo.get_by_id(scenario_id)
        if not s:
            raise to_http_exception(EntityNotFoundException("Scenario", scenario_id))
        return s

    def create_scenario(self, data: ScenarioCreate, created_by: int) -> Scenario:
        scenario = Scenario(
            name=data.name,
            description=data.description,
            scenario_type=data.scenario_type,
            parameters=json.dumps(data.parameters) if isinstance(data.parameters, dict) else data.parameters,
            created_by=created_by,
        )
        result = self._repo.create(scenario)
        self._bus.publish(EntityCreatedEvent(
            entity_type="scenario", entity_id=result.id, user_id=created_by,
        ))
        return result

    def update_scenario(self, scenario_id: int, data: ScenarioUpdate, user_id: int) -> Scenario:
        scenario = self.get_scenario(scenario_id)
        updates = data.model_dump(exclude_unset=True)
        if "parameters" in updates and isinstance(updates["parameters"], dict):
            updates["parameters"] = json.dumps(updates["parameters"])
        result = self._repo.update(scenario, updates)
        self._bus.publish(EntityUpdatedEvent(
            entity_type="scenario", entity_id=scenario_id, user_id=user_id, new_values=updates,
        ))
        return result

    def delete_scenario(self, scenario_id: int, user_id: int) -> None:
        scenario = self.get_scenario(scenario_id)
        self._repo.delete(scenario)
        self._bus.publish(EntityDeletedEvent(
            entity_type="scenario", entity_id=scenario_id, user_id=user_id,
        ))

    def run_scenario(self, scenario_id: int, user_id: int) -> Scenario:
        """Execute scenario simulation and store results."""
        scenario = self.get_scenario(scenario_id)
        params = json.loads(scenario.parameters) if isinstance(scenario.parameters, str) else scenario.parameters or {}

        demand_change_pct = self._to_decimal(params.get("demand_change_pct", 0))
        supply_capacity_pct = self._to_decimal(params.get("supply_capacity_pct", 0))
        price_change_pct = self._to_decimal(params.get("price_change_pct", 0))
        inventory_release_pct = self._to_decimal(params.get("inventory_release_pct", 0))

        target_period = self._parse_date(params.get("period")) or self._latest_demand_period() or date.today().replace(day=1)

        demand_plans = self._demand_repo.get_by_period(target_period)
        supply_plans = self._supply_repo.get_by_period(target_period)
        inventory_rows = self._inventory_repo.get_all_inventory()

        product_cache: Dict[int, object] = {}
        demand_qty_total = Decimal("0")
        base_revenue = Decimal("0")
        base_margin = Decimal("0")
        weighted_price_sum = Decimal("0")
        weighted_cost_sum = Decimal("0")

        for plan in demand_plans:
            qty_source = (
                plan.consensus_qty
                if plan.consensus_qty is not None
                else plan.adjusted_qty
                if plan.adjusted_qty is not None
                else plan.forecast_qty
            )
            qty = self._to_decimal(qty_source)
            demand_qty_total += qty

            product = product_cache.get(plan.product_id)
            if product is None:
                product = self._product_repo.get_by_id(plan.product_id)
                product_cache[plan.product_id] = product

            price = self._to_decimal(getattr(product, "selling_price", None), default=Decimal("0"))
            unit_cost = self._to_decimal(getattr(product, "unit_cost", None), default=Decimal("0"))
            base_revenue += qty * price
            base_margin += qty * (price - unit_cost)
            weighted_price_sum += qty * price
            weighted_cost_sum += qty * unit_cost

        base_supply_qty = sum((self._to_decimal(sp.planned_prod_qty) for sp in supply_plans), Decimal("0"))
        base_inventory_available_qty = Decimal("0")
        base_inventory = Decimal("0")
        for inv in inventory_rows:
            on_hand = self._to_decimal(inv.on_hand_qty)
            allocated = self._to_decimal(inv.allocated_qty)
            in_transit = self._to_decimal(inv.in_transit_qty)
            available = on_hand - allocated + in_transit
            if available < 0:
                available = Decimal("0")
            base_inventory_available_qty += available
            base_inventory += self._to_decimal(inv.valuation)

        if base_inventory <= 0 and demand_qty_total > 0:
            avg_unit_cost = weighted_cost_sum / demand_qty_total if demand_qty_total > 0 else Decimal("0")
            base_inventory = base_inventory_available_qty * avg_unit_cost

        base_effective_supply = base_supply_qty + base_inventory_available_qty
        base_service = Decimal("0")
        if demand_qty_total > 0:
            base_service = min(Decimal("100"), (base_effective_supply / demand_qty_total) * Decimal("100"))

        demand_multiplier = Decimal("1") + (demand_change_pct / Decimal("100"))
        supply_multiplier = Decimal("1") + (supply_capacity_pct / Decimal("100"))
        price_multiplier = Decimal("1") + (price_change_pct / Decimal("100"))
        inventory_release_multiplier = Decimal("1") + (inventory_release_pct / Decimal("100"))

        simulated_demand_qty = max(Decimal("0"), demand_qty_total * demand_multiplier)
        simulated_supply_qty = max(Decimal("0"), base_supply_qty * supply_multiplier)
        simulated_inventory_available_qty = max(Decimal("0"), base_inventory_available_qty * inventory_release_multiplier)
        simulated_effective_supply = simulated_supply_qty + simulated_inventory_available_qty

        avg_price = (weighted_price_sum / demand_qty_total) if demand_qty_total > 0 else Decimal("0")
        avg_unit_cost = (weighted_cost_sum / demand_qty_total) if demand_qty_total > 0 else Decimal("0")
        simulated_price = max(Decimal("0"), avg_price * price_multiplier)

        simulated_revenue = simulated_demand_qty * simulated_price
        simulated_margin = simulated_demand_qty * (simulated_price - avg_unit_cost)
        simulated_inventory = max(
            Decimal("0"),
            base_inventory + ((simulated_effective_supply - simulated_demand_qty) * avg_unit_cost),
        )
        simulated_service = Decimal("0")
        if simulated_demand_qty > 0:
            simulated_service = min(Decimal("100"), (simulated_effective_supply / simulated_demand_qty) * Decimal("100"))

        # Scenario trade-off layer (service vs inventory cost vs working capital)
        shortage_units = max(Decimal("0"), simulated_demand_qty - simulated_effective_supply)
        excess_units = max(Decimal("0"), simulated_effective_supply - simulated_demand_qty)
        carrying_rate_pct = self._to_decimal(params.get("inventory_carry_rate_pct", 18))
        stockout_penalty_per_unit = self._to_decimal(
            params.get("stockout_penalty_per_unit", (avg_price * Decimal("0.25")) if avg_price > 0 else Decimal("1"))
        )
        inventory_carrying_cost = (excess_units * avg_unit_cost * carrying_rate_pct / Decimal("100")).quantize(Decimal("0.01"))
        stockout_penalty_cost = (shortage_units * stockout_penalty_per_unit).quantize(Decimal("0.01"))
        working_capital_delta = (simulated_inventory - base_inventory).quantize(Decimal("0.01"))

        service_weight = self._to_decimal(params.get("service_weight", 0.45))
        cost_weight = self._to_decimal(params.get("cost_weight", 0.30))
        cash_weight = self._to_decimal(params.get("cash_weight", 0.25))
        service_score = (simulated_service - base_service)
        cost_score = -((inventory_carrying_cost + stockout_penalty_cost) / Decimal("1000"))
        cash_score = -(working_capital_delta / Decimal("1000"))
        composite_tradeoff_score = (
            service_weight * service_score
            + cost_weight * cost_score
            + cash_weight * cash_score
        ).quantize(Decimal("0.01"))

        inventory_ids = [inv.id for inv in inventory_rows]
        open_exceptions = [
            ex for ex in self._inventory_exception_repo.list_filtered(status="open")
            if ex.inventory_id in inventory_ids
        ]
        high_risk_count = len([ex for ex in open_exceptions if ex.severity == "high"])
        medium_risk_count = len([ex for ex in open_exceptions if ex.severity == "medium"])

        results = {
            "period": target_period.isoformat(),
            "inputs": {
                "demand_change_pct": float(demand_change_pct),
                "supply_capacity_pct": float(supply_capacity_pct),
                "price_change_pct": float(price_change_pct),
                "inventory_release_pct": float(inventory_release_pct),
            },
            "baseline": {
                "demand_qty": float(demand_qty_total),
                "supply_qty": float(base_supply_qty),
                "inventory_available_qty": float(base_inventory_available_qty),
                "effective_supply_qty": float(base_effective_supply),
                "revenue": float(base_revenue),
                "margin": float(base_margin),
                "inventory_value": float(base_inventory),
                "service_level": float(base_service),
            },
            "scenario": {
                "demand_qty": float(simulated_demand_qty),
                "supply_qty": float(simulated_supply_qty),
                "inventory_available_qty": float(simulated_inventory_available_qty),
                "effective_supply_qty": float(simulated_effective_supply),
                "revenue": float(simulated_revenue),
                "margin": float(simulated_margin),
                "inventory_value": float(simulated_inventory),
                "service_level": float(simulated_service),
            },
            "data_points": {
                "demand_plan_count": len(demand_plans),
                "supply_plan_count": len(supply_plans),
                "inventory_record_count": len(inventory_rows),
            },
            "revenue_impact": float(simulated_revenue - base_revenue),
            "margin_impact": float(simulated_margin - base_margin),
            "inventory_impact": float(simulated_inventory - base_inventory),
            "service_level_impact": float(simulated_service - base_service),
            "capacity_utilization_change": float(supply_capacity_pct),
            "tradeoff": {
                "inventory_carrying_cost": float(inventory_carrying_cost),
                "stockout_penalty_cost": float(stockout_penalty_cost),
                "working_capital_delta": float(working_capital_delta),
                "service_score": float(service_score),
                "cost_score": float(cost_score),
                "cash_score": float(cash_score),
                "composite_score": float(composite_tradeoff_score),
                "open_inventory_exceptions": len(open_exceptions),
                "high_risk_exception_count": high_risk_count,
                "medium_risk_exception_count": medium_risk_count,
            },
        }
        updates = {
            "status": "completed",
            "results": json.dumps(results),
            "revenue_impact": Decimal(str(results["revenue_impact"])),
            "margin_impact": Decimal(str(results["margin_impact"])),
            "inventory_impact": Decimal(str(results["inventory_impact"])),
            "service_level_impact": Decimal(str(results["service_level_impact"])),
        }
        result = self._repo.update(scenario, updates)
        self._bus.publish(PlanStatusChangedEvent(
            entity_type="scenario", entity_id=scenario_id, user_id=user_id,
            old_status=scenario.status, new_status="completed",
        ))
        return result

    def submit_scenario(self, scenario_id: int, user_id: int) -> Scenario:
        scenario = self.get_scenario(scenario_id)
        result = self._repo.update(scenario, {"status": "submitted"})
        self._bus.publish(PlanStatusChangedEvent(
            entity_type="scenario", entity_id=scenario_id, user_id=user_id,
            old_status=scenario.status, new_status="submitted",
        ))
        return result

    def approve_scenario(self, scenario_id: int, approver_id: int) -> Scenario:
        scenario = self.get_scenario(scenario_id)
        result = self._repo.update(scenario, {"status": "approved", "approved_by": approver_id})
        self._bus.publish(PlanStatusChangedEvent(
            entity_type="scenario", entity_id=scenario_id, user_id=approver_id,
            old_status=scenario.status, new_status="approved",
        ))
        return result

    def reject_scenario(self, scenario_id: int, approver_id: int) -> Scenario:
        scenario = self.get_scenario(scenario_id)
        result = self._repo.update(scenario, {"status": "rejected"})
        self._bus.publish(PlanStatusChangedEvent(
            entity_type="scenario", entity_id=scenario_id, user_id=approver_id,
            old_status=scenario.status, new_status="rejected",
        ))
        return result

    def compare_scenarios(self, ids: List[int]) -> List[dict]:
        scenarios = self._repo.get_by_ids(ids)
        return [
            {
                "id": s.id,
                "name": s.name,
                "scenario_type": s.scenario_type,
                "revenue_impact": float(s.revenue_impact or 0),
                "margin_impact": float(s.margin_impact or 0),
                "inventory_impact": float(s.inventory_impact or 0),
                "service_level_impact": float(s.service_level_impact or 0),
                "status": s.status,
            }
            for s in scenarios
        ]

    def get_tradeoff_summary(self, scenario_id: int) -> dict:
        scenario = self.get_scenario(scenario_id)
        if not scenario.results:
            return {
                "scenario_id": scenario.id,
                "status": scenario.status,
                "message": "Scenario has no computed results yet. Run the scenario first.",
                "tradeoff": None,
            }

        results = json.loads(scenario.results) if isinstance(scenario.results, str) else scenario.results
        tradeoff = (results or {}).get("tradeoff") or {}
        baseline = (results or {}).get("baseline") or {}
        scenario_view = (results or {}).get("scenario") or {}

        return {
            "scenario_id": scenario.id,
            "status": scenario.status,
            "period": (results or {}).get("period"),
            "tradeoff": {
                "inventory_carrying_cost": tradeoff.get("inventory_carrying_cost", 0),
                "stockout_penalty_cost": tradeoff.get("stockout_penalty_cost", 0),
                "working_capital_delta": tradeoff.get("working_capital_delta", 0),
                "composite_score": tradeoff.get("composite_score", 0),
                "open_inventory_exceptions": tradeoff.get("open_inventory_exceptions", 0),
                "high_risk_exception_count": tradeoff.get("high_risk_exception_count", 0),
            },
            "service_level": {
                "baseline": baseline.get("service_level", 0),
                "scenario": scenario_view.get("service_level", 0),
                "delta": (scenario_view.get("service_level", 0) or 0) - (baseline.get("service_level", 0) or 0),
            },
        }
