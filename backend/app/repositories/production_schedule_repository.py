from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.production_schedule import ProductionSchedule
from app.repositories.base import BaseRepository


class ProductionScheduleRepository(BaseRepository[ProductionSchedule]):
    def __init__(self, db: Session):
        super().__init__(ProductionSchedule, db)

    def list_filtered(
        self,
        product_id: Optional[int] = None,
        period: Optional[date] = None,
        supply_plan_id: Optional[int] = None,
        workcenter: Optional[str] = None,
        line: Optional[str] = None,
        shift: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[ProductionSchedule]:
        q = self.db.query(ProductionSchedule)
        if product_id is not None:
            q = q.filter(ProductionSchedule.product_id == product_id)
        if period is not None:
            q = q.filter(ProductionSchedule.period == period)
        if supply_plan_id is not None:
            q = q.filter(ProductionSchedule.supply_plan_id == supply_plan_id)
        if workcenter is not None:
            q = q.filter(ProductionSchedule.workcenter == workcenter)
        if line is not None:
            q = q.filter(ProductionSchedule.line == line)
        if shift is not None:
            q = q.filter(ProductionSchedule.shift == shift)
        if status is not None:
            q = q.filter(ProductionSchedule.status == status)
        return q.order_by(ProductionSchedule.period, ProductionSchedule.sequence_order).all()

    def delete_by_supply_plan(self, supply_plan_id: int) -> None:
        (
            self.db.query(ProductionSchedule)
            .filter(ProductionSchedule.supply_plan_id == supply_plan_id)
            .delete(synchronize_session=False)
        )
        self.db.commit()
