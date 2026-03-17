from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.agentic_schedule_recommendation import AgenticScheduleRecommendation
from app.repositories.base import BaseRepository


class AgenticScheduleRecommendationRepository(BaseRepository[AgenticScheduleRecommendation]):
    def __init__(self, db: Session):
        super().__init__(AgenticScheduleRecommendation, db)

    def get_by_recommendation_id(self, recommendation_id: str) -> Optional[AgenticScheduleRecommendation]:
        return (
            self.db.query(AgenticScheduleRecommendation)
            .filter(AgenticScheduleRecommendation.recommendation_id == recommendation_id)
            .first()
        )

    def list_filtered(
        self,
        status: Optional[str] = None,
        supply_plan_id: Optional[int] = None,
        product_id: Optional[int] = None,
    ) -> List[AgenticScheduleRecommendation]:
        q = self.db.query(AgenticScheduleRecommendation)
        if status:
            q = q.filter(AgenticScheduleRecommendation.status == status)
        if supply_plan_id:
            q = q.filter(AgenticScheduleRecommendation.supply_plan_id == supply_plan_id)
        if product_id:
            q = q.filter(AgenticScheduleRecommendation.product_id == product_id)
        return q.order_by(AgenticScheduleRecommendation.created_at.desc()).all()
