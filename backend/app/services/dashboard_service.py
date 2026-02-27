"""
Dashboard Service — Service Layer (SRP / DIP)
Aggregates data from multiple repositories for the executive dashboard.
"""
from decimal import Decimal
from sqlalchemy.orm import Session

from app.repositories.demand_repository import DemandPlanRepository
from app.repositories.supply_repository import SupplyPlanRepository
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.kpi_repository import KPIMetricRepository
from app.repositories.sop_cycle_repository import SOPCycleRepository


class DashboardService:

    def __init__(self, db: Session):
        self._demand_repo = DemandPlanRepository(db)
        self._supply_repo = SupplyPlanRepository(db)
        self._inventory_repo = InventoryRepository(db)
        self._kpi_repo = KPIMetricRepository(db)
        self._sop_repo = SOPCycleRepository(db)

    def get_summary(self) -> dict:
        """Executive dashboard summary — KPIs, plan counts, inventory health."""
        # Plan status counts
        demand_draft = self._demand_repo.count_by_status("draft")
        demand_submitted = self._demand_repo.count_by_status("submitted")
        demand_approved = self._demand_repo.count_by_status("approved")

        # Inventory health
        all_inv = self._inventory_repo.get_all_inventory()
        total_inv = len(all_inv)
        inv_counts = {"normal": 0, "low": 0, "critical": 0, "excess": 0}
        total_value = Decimal("0")
        for inv in all_inv:
            inv_counts[inv.status] = inv_counts.get(inv.status, 0) + 1
            total_value += inv.valuation or Decimal("0")

        # Latest KPIs
        forecast_accuracy = self._kpi_repo.get_latest_by_name("Forecast Accuracy")
        otif = self._kpi_repo.get_latest_by_name("OTIF")

        # Active S&OP cycle
        active_cycle = self._sop_repo.get_active_cycle()

        return {
            "demand_plans": {
                "draft": demand_draft,
                "submitted": demand_submitted,
                "approved": demand_approved,
                "total": demand_draft + demand_submitted + demand_approved,
            },
            "inventory_health": {
                "total_products": total_inv,
                "normal": inv_counts["normal"],
                "low": inv_counts["low"],
                "critical": inv_counts["critical"],
                "excess": inv_counts["excess"],
                "total_value": float(total_value),
            },
            "kpis": {
                "forecast_accuracy": float(forecast_accuracy.value) if forecast_accuracy else None,
                "otif": float(otif.value) if otif else None,
            },
            "sop_cycle": {
                "id": active_cycle.id if active_cycle else None,
                "name": active_cycle.cycle_name if active_cycle else None,
                "current_step": active_cycle.current_step if active_cycle else None,
                "status": active_cycle.overall_status if active_cycle else None,
            } if active_cycle else None,
        }

    def get_alerts(self) -> dict:
        """Aggregate all active alerts across modules."""
        critical_inv = self._inventory_repo.get_critical()
        low_inv = self._inventory_repo.get_low()
        kpi_alerts = []
        for m in self._kpi_repo.get_with_targets():
            if m.target and m.value:
                variance_pct = float((m.value - m.target) / m.target * 100) if m.target != 0 else 0
                if abs(variance_pct) > 15:
                    kpi_alerts.append({
                        "type": "kpi",
                        "severity": "critical" if abs(variance_pct) > 25 else "warning",
                        "message": f"{m.metric_name} is {abs(variance_pct):.1f}% off target",
                        "metric": m.metric_name,
                        "value": float(m.value),
                        "target": float(m.target),
                    })
        return {
            "inventory_critical": [
                {"product_id": i.product_id, "location": i.location, "on_hand": float(i.on_hand_qty)}
                for i in critical_inv
            ],
            "inventory_low": [
                {"product_id": i.product_id, "location": i.location, "on_hand": float(i.on_hand_qty)}
                for i in low_inv
            ],
            "kpi_alerts": kpi_alerts,
            "total_alerts": len(critical_inv) + len(low_inv) + len(kpi_alerts),
        }

    def get_sop_status(self) -> dict:
        """Return current S&OP cycle status for the dashboard widget."""
        cycle = self._sop_repo.get_active_cycle()
        if not cycle:
            return {"active": False, "message": "No active S&OP cycle"}
        return {
            "active": True,
            "id": cycle.id,
            "name": cycle.cycle_name,
            "period": str(cycle.period),
            "current_step": cycle.current_step,
            "steps": [
                {"step": 1, "name": "Data Gathering", "status": cycle.step_1_status, "due_date": str(cycle.step_1_due_date) if cycle.step_1_due_date else None},
                {"step": 2, "name": "Demand Review", "status": cycle.step_2_status, "due_date": str(cycle.step_2_due_date) if cycle.step_2_due_date else None},
                {"step": 3, "name": "Supply Review", "status": cycle.step_3_status, "due_date": str(cycle.step_3_due_date) if cycle.step_3_due_date else None},
                {"step": 4, "name": "Pre-S&OP", "status": cycle.step_4_status, "due_date": str(cycle.step_4_due_date) if cycle.step_4_due_date else None},
                {"step": 5, "name": "Executive S&OP", "status": cycle.step_5_status, "due_date": str(cycle.step_5_due_date) if cycle.step_5_due_date else None},
            ],
            "overall_status": cycle.overall_status,
        }
