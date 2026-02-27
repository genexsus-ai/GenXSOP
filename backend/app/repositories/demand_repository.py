"""
Demand Plan Repository — Repository Pattern (GoF)
Encapsulates all demand-plan data access logic.
"""
from typing import Optional, List, Tuple
from datetime import date
from math import ceil
from sqlalchemy.orm import Session
from app.repositories.base import BaseRepository
from app.models.demand_plan import DemandPlan


class DemandPlanRepository(BaseRepository[DemandPlan]):
    """
    Concrete repository for DemandPlan.
    All SQLAlchemy queries for demand plans live here — nowhere else.
    """

    def __init__(self, db: Session):
        super().__init__(DemandPlan, db)

    # ── Filtered Queries ─────────────────────────────────────────────────────

    def list_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        product_id: Optional[int] = None,
        region: Optional[str] = None,
        channel: Optional[str] = None,
        status: Optional[str] = None,
        period_from: Optional[date] = None,
        period_to: Optional[date] = None,
    ) -> Tuple[List[DemandPlan], int]:
        """Return paginated demand plans with optional filters. Returns (items, total)."""
        q = self.db.query(DemandPlan)
        if product_id:
            q = q.filter(DemandPlan.product_id == product_id)
        if region:
            q = q.filter(DemandPlan.region == region)
        if channel:
            q = q.filter(DemandPlan.channel == channel)
        if status:
            q = q.filter(DemandPlan.status == status)
        if period_from:
            q = q.filter(DemandPlan.period >= period_from)
        if period_to:
            q = q.filter(DemandPlan.period <= period_to)
        q = q.order_by(DemandPlan.period.desc())
        total = q.count()
        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def get_by_product_and_period(
        self, product_id: int, period: date
    ) -> Optional[DemandPlan]:
        """Fetch a single demand plan by product + period."""
        return (
            self.db.query(DemandPlan)
            .filter(
                DemandPlan.product_id == product_id,
                DemandPlan.period == period,
            )
            .first()
        )

    def get_by_period(self, period: date) -> List[DemandPlan]:
        """Fetch all demand plans for a given period."""
        return (
            self.db.query(DemandPlan)
            .filter(DemandPlan.period == period)
            .all()
        )

    def get_submitted(self) -> List[DemandPlan]:
        """Fetch all plans awaiting approval."""
        return (
            self.db.query(DemandPlan)
            .filter(DemandPlan.status == "submitted")
            .all()
        )

    def count_by_status(self, status: str) -> int:
        """Count plans by status."""
        return (
            self.db.query(DemandPlan)
            .filter(DemandPlan.status == status)
            .count()
        )

    def get_with_actuals(self, product_id: int) -> List[DemandPlan]:
        """Fetch historical demand plans that have actual quantities (for ML training)."""
        return (
            self.db.query(DemandPlan)
            .filter(
                DemandPlan.product_id == product_id,
                DemandPlan.actual_qty.isnot(None),
            )
            .order_by(DemandPlan.period.asc())
            .all()
        )

    def get_all_for_product(self, product_id: int) -> List[DemandPlan]:
        """Fetch all demand plans for a product ordered by period."""
        return (
            self.db.query(DemandPlan)
            .filter(DemandPlan.product_id == product_id)
            .order_by(DemandPlan.period.asc())
            .all()
        )
