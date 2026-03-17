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
