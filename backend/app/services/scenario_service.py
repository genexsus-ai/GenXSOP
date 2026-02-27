"""
Scenario Service — Service Layer (SRP / DIP)
"""
import json
from math import ceil
from typing import List
from decimal import Decimal
from sqlalchemy.orm import Session

from app.repositories.scenario_repository import ScenarioRepository
from app.models.scenario import Scenario
from app.schemas.scenario import ScenarioCreate, ScenarioUpdate, ScenarioListResponse
from app.core.exceptions import EntityNotFoundException, to_http_exception
from app.utils.events import get_event_bus, EntityCreatedEvent, EntityUpdatedEvent, EntityDeletedEvent, PlanStatusChangedEvent


class ScenarioService:

    def __init__(self, db: Session):
        self._repo = ScenarioRepository(db)
        self._bus = get_event_bus()

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
        demand_change = params.get("demand_change_pct", 0) / 100
        supply_change = params.get("supply_capacity_pct", 0) / 100
        price_change = params.get("price_change_pct", 0) / 100
        base_revenue = Decimal("12500000")
        base_margin = Decimal("3800000")
        base_inventory = Decimal("2100000")
        base_service = Decimal("94.2")
        results = {
            "revenue_impact": float(base_revenue * Decimal(str(demand_change + price_change))),
            "margin_impact": float(base_margin * Decimal(str(demand_change * 0.8 + price_change))),
            "inventory_impact": float(base_inventory * Decimal(str(demand_change * 0.5))),
            "service_level_impact": float(base_service + Decimal(str(-demand_change * 5 + supply_change * 3))),
            "capacity_utilization_change": float(supply_change * 100),
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
