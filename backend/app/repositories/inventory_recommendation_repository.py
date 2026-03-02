"""
Inventory Policy Recommendation Repository
"""
from typing import List, Optional
from sqlalchemy.orm import Session

from app.repositories.base import BaseRepository
from app.models.inventory_policy_recommendation import InventoryPolicyRecommendation


class InventoryRecommendationRepository(BaseRepository[InventoryPolicyRecommendation]):

    def __init__(self, db: Session):
        super().__init__(InventoryPolicyRecommendation, db)

    def list_filtered(
        self,
        status: Optional[str] = None,
        inventory_id: Optional[int] = None,
    ) -> List[InventoryPolicyRecommendation]:
        q = self.db.query(InventoryPolicyRecommendation)
        if status:
            q = q.filter(InventoryPolicyRecommendation.status == status)
        if inventory_id:
            q = q.filter(InventoryPolicyRecommendation.inventory_id == inventory_id)
        return q.order_by(InventoryPolicyRecommendation.created_at.desc()).all()

    def get_latest_pending_by_inventory(
        self,
        inventory_id: int,
    ) -> Optional[InventoryPolicyRecommendation]:
        return (
            self.db.query(InventoryPolicyRecommendation)
            .filter(
                InventoryPolicyRecommendation.inventory_id == inventory_id,
                InventoryPolicyRecommendation.status == "pending",
            )
            .order_by(InventoryPolicyRecommendation.created_at.desc())
            .first()
        )
