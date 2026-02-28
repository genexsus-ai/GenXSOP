"""
Forecast Repository — Repository Pattern (GoF)
"""
from typing import Optional, List
from datetime import date
from sqlalchemy.orm import Session
from app.repositories.base import BaseRepository
from app.models.forecast import Forecast


class ForecastRepository(BaseRepository[Forecast]):

    def __init__(self, db: Session):
        super().__init__(Forecast, db)

    def list_filtered(
        self,
        product_id: Optional[int] = None,
        model_type: Optional[str] = None,
        period_from: Optional[date] = None,
        period_to: Optional[date] = None,
    ) -> List[Forecast]:
        q = self.db.query(Forecast)
        if product_id:
            q = q.filter(Forecast.product_id == product_id)
        if model_type:
            q = q.filter(Forecast.model_type == model_type)
        if period_from:
            q = q.filter(Forecast.period >= period_from)
        if period_to:
            q = q.filter(Forecast.period <= period_to)
        return q.order_by(Forecast.period.asc()).all()

    def delete_by_product_model_period(
        self, product_id: int, model_type: str, period: date
    ) -> None:
        """Remove existing forecast before inserting a new one (upsert pattern)."""
        self.db.query(Forecast).filter(
            Forecast.product_id == product_id,
            Forecast.model_type == model_type,
            Forecast.period == period,
        ).delete()

    def delete_by_product(self, product_id: int, commit: bool = True) -> int:
        deleted = self.db.query(Forecast).filter(
            Forecast.product_id == product_id,
        ).delete(synchronize_session=False)
        if commit:
            self.db.commit()
        return int(deleted or 0)

    def get_with_mape(
        self,
        product_id: Optional[int] = None,
        model_type: Optional[str] = None,
    ) -> List[Forecast]:
        q = self.db.query(Forecast).filter(Forecast.mape.isnot(None))
        if product_id:
            q = q.filter(Forecast.product_id == product_id)
        if model_type:
            q = q.filter(Forecast.model_type == model_type)
        return q.all()
