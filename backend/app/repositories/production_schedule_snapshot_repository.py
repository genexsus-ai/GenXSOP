from typing import Optional, List

from sqlalchemy.orm import Session

from app.models.production_schedule_snapshot import ProductionScheduleSnapshot
from app.repositories.base import BaseRepository


class ProductionScheduleSnapshotRepository(BaseRepository[ProductionScheduleSnapshot]):
    def __init__(self, db: Session):
        super().__init__(ProductionScheduleSnapshot, db)

    def list_by_supply_plan(self, supply_plan_id: int) -> List[ProductionScheduleSnapshot]:
        return (
            self.db.query(ProductionScheduleSnapshot)
            .filter(ProductionScheduleSnapshot.supply_plan_id == supply_plan_id)
            .order_by(ProductionScheduleSnapshot.version_number.asc())
            .all()
        )

    def get_by_supply_plan_and_version(
        self,
        supply_plan_id: int,
        version_number: int,
    ) -> Optional[ProductionScheduleSnapshot]:
        return (
            self.db.query(ProductionScheduleSnapshot)
            .filter(
                ProductionScheduleSnapshot.supply_plan_id == supply_plan_id,
                ProductionScheduleSnapshot.version_number == version_number,
            )
            .first()
        )

    def latest_for_supply_plan(self, supply_plan_id: int) -> Optional[ProductionScheduleSnapshot]:
        return (
            self.db.query(ProductionScheduleSnapshot)
            .filter(ProductionScheduleSnapshot.supply_plan_id == supply_plan_id)
            .order_by(ProductionScheduleSnapshot.version_number.desc())
            .first()
        )
