from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Boolean,
    Numeric,
    Index,
    func,
)

from app.database import Base


class ForecastRunAudit(Base):
    __tablename__ = "forecast_run_audits"
    __table_args__ = (
        Index("ix_forecast_run_audits_product_created", "product_id", "created_at"),
        Index("ix_forecast_run_audits_fallback", "fallback_used", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    requested_model = Column(String(50), nullable=True)
    selected_model = Column(String(50), nullable=False)
    horizon = Column(Integer, nullable=False)

    advisor_enabled = Column(Boolean, nullable=False, default=False)
    fallback_used = Column(Boolean, nullable=False, default=False)
    advisor_confidence = Column(Numeric(6, 4), nullable=True)
    selection_reason = Column(Text, nullable=True)

    history_months = Column(Integer, nullable=False)
    records_created = Column(Integer, nullable=False)

    warnings_json = Column(Text, nullable=True)
    candidate_metrics_json = Column(Text, nullable=True)
    data_quality_flags_json = Column(Text, nullable=True)

    created_at = Column(DateTime, default=func.now(), nullable=False)