"""
Scenario Repository — Repository Pattern (GoF)
"""
from typing import List, Tuple
from sqlalchemy.orm import Session
from app.repositories.base import BaseRepository
from app.models.scenario import Scenario


class ScenarioRepository(BaseRepository[Scenario]):

    def __init__(self, db: Session):
        super().__init__(Scenario, db)

    def list_paginated(self, page: int = 1, page_size: int = 20) -> Tuple[List[Scenario], int]:
        q = self.db.query(Scenario).order_by(Scenario.created_at.desc())
        total = q.count()
        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def get_by_ids(self, ids: List[int]) -> List[Scenario]:
        return self.db.query(Scenario).filter(Scenario.id.in_(ids)).all()

    def get_by_status(self, status: str) -> List[Scenario]:
        return self.db.query(Scenario).filter(Scenario.status == status).all()
