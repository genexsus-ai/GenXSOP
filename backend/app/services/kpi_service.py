"""
KPI Service — Service Layer (SRP / DIP)
"""
from typing import Optional, List
from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Session

from app.repositories.kpi_repository import KPIMetricRepository
from app.models.kpi_metric import KPIMetric
from app.schemas.kpi import KPIMetricCreate, KPIDashboardData, KPITargetRequest
from app.core.exceptions import EntityNotFoundException, to_http_exception
from app.utils.events import get_event_bus, EntityCreatedEvent


class KPIService:

    def __init__(self, db: Session):
        self._repo = KPIMetricRepository(db)
        self._bus = get_event_bus()

    def list_metrics(
        self,
        category: Optional[str] = None,
        period_from: Optional[date] = None,
        period_to: Optional[date] = None,
    ) -> List[KPIMetric]:
        return self._repo.list_filtered(category=category, period_from=period_from, period_to=period_to)

    def get_metric(self, metric_id: int) -> KPIMetric:
        m = self._repo.get_by_id(metric_id)
        if not m:
            raise to_http_exception(EntityNotFoundException("KPIMetric", metric_id))
        return m

    def create_metric(self, data: KPIMetricCreate, user_id: int) -> KPIMetric:
        variance = None
        variance_pct = None
        trend = None
        if data.target is not None:
            variance = data.value - data.target
            variance_pct = (variance / data.target * 100) if data.target != 0 else None
        if data.previous_value is not None and data.previous_value != 0:
            change = data.value - data.previous_value
            trend = "improving" if change > 0 else ("declining" if change < 0 else "stable")
        metric = KPIMetric(
            **data.model_dump(),
            variance=variance,
            variance_pct=variance_pct,
            trend=trend,
        )
        result = self._repo.create(metric)
        self._bus.publish(EntityCreatedEvent(
            entity_type="kpi_metric", entity_id=result.id, user_id=user_id,
        ))
        return result

    def get_dashboard(self) -> KPIDashboardData:
        """Return KPIs grouped by category for the dashboard."""
        return KPIDashboardData(
            demand_kpis=self._repo.get_by_category("demand"),
            supply_kpis=self._repo.get_by_category("supply"),
            inventory_kpis=self._repo.get_by_category("inventory"),
            service_kpis=self._repo.get_by_category("service"),
            financial_kpis=self._repo.get_by_category("financial"),
        )

    def get_alerts(self) -> List[dict]:
        """Return KPIs that are breaching their targets."""
        metrics = self._repo.get_with_targets()
        alerts = []
        for m in metrics:
            if m.target is None or m.value is None:
                continue
            variance_pct = float((m.value - m.target) / m.target * 100) if m.target != 0 else 0
            if abs(variance_pct) > 10:
                severity = "critical" if abs(variance_pct) > 20 else "warning"
                alerts.append({
                    "metric_name": m.metric_name,
                    "category": m.metric_category,
                    "value": float(m.value),
                    "target": float(m.target),
                    "variance_pct": round(variance_pct, 2),
                    "severity": severity,
                    "period": str(m.period),
                })
        return alerts

    def set_target(self, body: KPITargetRequest, user_id: int) -> KPIMetric:
        """Update the target for the most recent KPI metric by name."""
        metric = self._repo.get_latest_by_name(body.metric_name)
        if not metric:
            raise to_http_exception(EntityNotFoundException("KPIMetric", body.metric_name))
        variance = metric.value - body.target
        variance_pct = (variance / body.target * 100) if body.target != 0 else None
        return self._repo.update(metric, {
            "target": body.target,
            "variance": variance,
            "variance_pct": variance_pct,
        })
