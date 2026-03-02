"""
Inventory Policy Exception Repository
"""
from typing import List, Optional
from sqlalchemy.orm import Session

from app.repositories.base import BaseRepository
from app.models.inventory_policy_exception import InventoryPolicyException


class InventoryExceptionRepository(BaseRepository[InventoryPolicyException]):

    def __init__(self, db: Session):
        super().__init__(InventoryPolicyException, db)

    def list_filtered(
        self,
        status: Optional[str] = None,
        owner_user_id: Optional[int] = None,
        inventory_id: Optional[int] = None,
    ) -> List[InventoryPolicyException]:
        q = self.db.query(InventoryPolicyException)
        if status:
            q = q.filter(InventoryPolicyException.status == status)
        if owner_user_id:
            q = q.filter(InventoryPolicyException.owner_user_id == owner_user_id)
        if inventory_id:
            q = q.filter(InventoryPolicyException.inventory_id == inventory_id)
        return q.all()

    def get_open_by_inventory_and_type(
        self,
        inventory_id: int,
        exception_type: str,
    ) -> Optional[InventoryPolicyException]:
        return (
            self.db.query(InventoryPolicyException)
            .filter(
                InventoryPolicyException.inventory_id == inventory_id,
                InventoryPolicyException.exception_type == exception_type,
                InventoryPolicyException.status.in_(["open", "in_progress"]),
            )
            .order_by(InventoryPolicyException.updated_at.desc())
            .first()
        )
