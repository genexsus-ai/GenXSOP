from typing import Optional, List

from sqlalchemy.orm import Session

from app.models.production_event import ProductionEvent
from app.repositories.base import BaseRepository


class ProductionEventRepository(BaseRepository[ProductionEvent]):
    def __init__(self, db: Session):
        super().__init__(ProductionEvent, db)

    def get_by_event_id(self, event_id: str) -> Optional[ProductionEvent]:
        return (
            self.db.query(ProductionEvent)
            .filter(ProductionEvent.event_id == event_id)
            .first()
        )

    def get_by_idempotency_key(self, idempotency_key: str) -> Optional[ProductionEvent]:
        return (
            self.db.query(ProductionEvent)
            .filter(ProductionEvent.idempotency_key == idempotency_key)
            .first()
        )

    def list_recent(self, limit: int = 100) -> List[ProductionEvent]:
        return (
            self.db.query(ProductionEvent)
            .order_by(ProductionEvent.event_timestamp.desc())
            .limit(limit)
            .all()
        )

    def latest_for_scope(
        self,
        event_source: str,
        plant_id: Optional[str] = None,
        line_id: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> Optional[ProductionEvent]:
        query = self.db.query(ProductionEvent).filter(ProductionEvent.event_source == event_source)
        if plant_id:
            query = query.filter(ProductionEvent.plant_id == plant_id)
        if line_id:
            query = query.filter(ProductionEvent.line_id == line_id)
        if resource_id:
            query = query.filter(ProductionEvent.resource_id == resource_id)
        return query.order_by(ProductionEvent.event_timestamp.desc()).first()
