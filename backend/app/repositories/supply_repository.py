"""
Supply Plan Repository — Repository Pattern (GoF)
"""
from typing import Optional, List, Tuple
from datetime import date
from sqlalchemy.orm import Session
from app.repositories.base import BaseRepository
from app.models.supply_plan import SupplyPlan


class SupplyPlanRepository(BaseRepository[SupplyPlan]):

    def __init__(self, db: Session):
        super().__init__(SupplyPlan, db)

    def list_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        product_id: Optional[int] = None,
        location: Optional[str] = None,
        status: Optional[str] = None,
        period_from: Optional[date] = None,
        period_to: Optional[date] = None,
    ) -> Tuple[List[SupplyPlan], int]:
        q = self.db.query(SupplyPlan)
        if product_id:
            q = q.filter(SupplyPlan.product_id == product_id)
        if location:
            q = q.filter(SupplyPlan.location == location)
        if status:
            q = q.filter(SupplyPlan.status == status)
        if period_from:
            q = q.filter(SupplyPlan.period >= period_from)
        if period_to:
            q = q.filter(SupplyPlan.period <= period_to)
        q = q.order_by(SupplyPlan.period.desc())
        total = q.count()
        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def get_by_period(self, period: date) -> List[SupplyPlan]:
        return (
            self.db.query(SupplyPlan)
            .filter(SupplyPlan.period == period)
            .all()
        )

    def get_by_product_and_period(self, product_id: int, period: date) -> Optional[SupplyPlan]:
        return (
            self.db.query(SupplyPlan)
            .filter(SupplyPlan.product_id == product_id, SupplyPlan.period == period)
            .first()
        )
