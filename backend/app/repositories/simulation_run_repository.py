from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.simulation_run import SimulationRun
from app.repositories.base import BaseRepository


class SimulationRunRepository(BaseRepository[SimulationRun]):
    def __init__(self, db: Session):
        super().__init__(SimulationRun, db)

    def get_by_simulation_id(self, simulation_id: str) -> Optional[SimulationRun]:
        return (
            self.db.query(SimulationRun)
            .filter(SimulationRun.simulation_id == simulation_id)
            .first()
        )

    def list_filtered(
        self,
        recommendation_id: Optional[str] = None,
        status: Optional[str] = None,
        scenario_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[SimulationRun]:
        query = self.db.query(SimulationRun)
        if recommendation_id:
            query = query.filter(SimulationRun.recommendation_id == recommendation_id)
        if status:
            query = query.filter(SimulationRun.status == status)
        if scenario_name:
            query = query.filter(SimulationRun.scenario_name == scenario_name)
        return query.order_by(SimulationRun.created_at.desc()).limit(limit).all()
