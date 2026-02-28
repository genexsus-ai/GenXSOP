"""
Forecast Consensus Repository — Repository Pattern (GoF)
"""
from typing import Optional, List
from datetime import date
from sqlalchemy.orm import Session

from app.repositories.base import BaseRepository
from app.models.forecast_consensus import ForecastConsensus


class ForecastConsensusRepository(BaseRepository[ForecastConsensus]):
    def __init__(self, db: Session):
        super().__init__(ForecastConsensus, db)

    def list_filtered(
        self,
        product_id: Optional[int] = None,
        forecast_run_audit_id: Optional[int] = None,
        status: Optional[str] = None,
        period_from: Optional[date] = None,
        period_to: Optional[date] = None,
    ) -> List[ForecastConsensus]:
        q = self.db.query(ForecastConsensus)
        if product_id:
            q = q.filter(ForecastConsensus.product_id == product_id)
        if forecast_run_audit_id:
            q = q.filter(ForecastConsensus.forecast_run_audit_id == forecast_run_audit_id)
        if status:
            q = q.filter(ForecastConsensus.status == status)
        if period_from:
            q = q.filter(ForecastConsensus.period >= period_from)
        if period_to:
            q = q.filter(ForecastConsensus.period <= period_to)
        return q.order_by(ForecastConsensus.period.asc(), ForecastConsensus.version.desc()).all()

    def get_latest(
        self,
        *,
        period: date,
        product_id: Optional[int] = None,
        forecast_run_audit_id: Optional[int] = None,
    ) -> Optional[ForecastConsensus]:
        q = self.db.query(ForecastConsensus).filter(ForecastConsensus.period == period)
        if forecast_run_audit_id is not None:
            q = q.filter(ForecastConsensus.forecast_run_audit_id == forecast_run_audit_id)
        elif product_id is not None:
            q = q.filter(ForecastConsensus.product_id == product_id)
        return q.order_by(ForecastConsensus.version.desc()).first()

    def delete_by_product(self, product_id: int, commit: bool = True) -> int:
        deleted = self.db.query(ForecastConsensus).filter(
            ForecastConsensus.product_id == product_id,
        ).delete(synchronize_session=False)
        if commit:
            self.db.commit()
        return int(deleted or 0)
