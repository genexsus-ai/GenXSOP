from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, CheckConstraint, Index, func
from app.database import Base


class ForecastJob(Base):
    __tablename__ = "forecast_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed', 'cancelled')",
            name="ck_forecast_jobs_status",
        ),
        CheckConstraint("horizon >= 1", name="ck_forecast_jobs_horizon_min_1"),
        Index("ix_forecast_jobs_status_created_at", "status", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(64), unique=True, index=True, nullable=False)
    status = Column(String(20), nullable=False, index=True)

    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    horizon = Column(Integer, nullable=False)
    model_type = Column(String(50), nullable=True)
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    error = Column(Text, nullable=True)
    result_json = Column(Text, nullable=True)

    created_at = Column(DateTime, default=func.now(), nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
