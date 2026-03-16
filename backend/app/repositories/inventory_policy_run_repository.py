"""Inventory Policy Run Repository

Provides persisted inventory optimization run history.
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.inventory_policy_run import InventoryPolicyRun
from app.repositories.base import BaseRepository


class InventoryPolicyRunRepository(BaseRepository[InventoryPolicyRun]):
    def __init__(self, db: Session):
        super().__init__(InventoryPolicyRun, db)

    def get_by_run_id(self, run_id: str) -> Optional[InventoryPolicyRun]:
        return self.db.query(InventoryPolicyRun).filter(InventoryPolicyRun.run_id == run_id).first()

    def list_recent(self, limit: int = 50, status: Optional[str] = None) -> List[InventoryPolicyRun]:
        q = self.db.query(InventoryPolicyRun)
        if status:
            q = q.filter(InventoryPolicyRun.status == status)
        return q.order_by(InventoryPolicyRun.created_at.desc()).limit(limit).all()
