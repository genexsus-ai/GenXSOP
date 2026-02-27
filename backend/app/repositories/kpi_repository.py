"""
KPI Metric Repository — Repository Pattern (GoF)
"""
from typing import Optional, List
from datetime import date
from sqlalchemy.orm import Session
from app.repositories.base import BaseRepository
from app.models.kpi_metric import KPIMetric


class KPIMetricRepository(BaseRepository[KPIMetric]):

    def __init__(self, db: Session):
        super().__init__(KPIMetric, db)

    def list_filtered(
        self,
        category: Optional[str] = None,
        period_from: Optional[date] = None,
        period_to: Optional[date] = None,
    ) -> List[KPIMetric]:
        q = self.db.query(KPIMetric)
        if category:
            q = q.filter(KPIMetric.metric_category == category)
        if period_from:
            q = q.filter(KPIMetric.period >= period_from)
        if period_to:
            q = q.filter(KPIMetric.period <= period_to)
        return q.order_by(KPIMetric.period.desc()).all()

    def get_by_category(self, category: str, limit: int = 10) -> List[KPIMetric]:
        return (
            self.db.query(KPIMetric)
            .filter(KPIMetric.metric_category == category)
            .order_by(KPIMetric.period.desc())
            .limit(limit)
            .all()
        )

    def get_by_name(self, metric_name: str, limit: int = 12) -> List[KPIMetric]:
        return (
            self.db.query(KPIMetric)
            .filter(KPIMetric.metric_name == metric_name)
            .order_by(KPIMetric.period.desc())
            .limit(limit)
            .all()
        )

    def get_latest_by_name(self, metric_name: str) -> Optional[KPIMetric]:
        return (
            self.db.query(KPIMetric)
            .filter(KPIMetric.metric_name == metric_name)
            .order_by(KPIMetric.period.desc())
            .first()
        )

    def get_by_name_and_period(self, metric_name: str, period: date) -> Optional[KPIMetric]:
        return (
            self.db.query(KPIMetric)
            .filter(KPIMetric.metric_name == metric_name, KPIMetric.period == period)
            .first()
        )

    def get_with_targets(self) -> List[KPIMetric]:
        """Return all KPIs that have a target set (for alert evaluation)."""
        return self.db.query(KPIMetric).filter(KPIMetric.target.isnot(None)).all()
