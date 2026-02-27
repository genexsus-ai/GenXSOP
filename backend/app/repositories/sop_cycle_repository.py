"""
S&OP Cycle Repository — Repository Pattern (GoF)
"""
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from app.repositories.base import BaseRepository
from app.models.sop_cycle import SOPCycle


class SOPCycleRepository(BaseRepository[SOPCycle]):

    def __init__(self, db: Session):
        super().__init__(SOPCycle, db)

    def list_paginated(self, page: int = 1, page_size: int = 20) -> Tuple[List[SOPCycle], int]:
        q = self.db.query(SOPCycle).order_by(SOPCycle.period.desc())
        total = q.count()
        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def get_active_cycle(self) -> Optional[SOPCycle]:
        """Return the most recent active S&OP cycle."""
        return (
            self.db.query(SOPCycle)
            .filter(SOPCycle.overall_status == "active")
            .order_by(SOPCycle.period.desc())
            .first()
        )

    def get_by_status(self, status: str) -> List[SOPCycle]:
        return self.db.query(SOPCycle).filter(SOPCycle.overall_status == status).all()
