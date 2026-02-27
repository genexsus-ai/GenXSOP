from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    DateTime,
    Date,
    ForeignKey,
    Text,
    CheckConstraint,
    UniqueConstraint,
    Index,
    func,
)
from app.database import Base


class Forecast(Base):
    __tablename__ = "forecasts"
    __table_args__ = (
        UniqueConstraint(
            "product_id",
            "period",
            "model_type",
            name="uq_forecasts_business_key",
        ),
        CheckConstraint("predicted_qty >= 0", name="ck_forecasts_predicted_qty_non_negative"),
        CheckConstraint(
            "lower_bound IS NULL OR lower_bound >= 0",
            name="ck_forecasts_lower_bound_non_negative",
        ),
        CheckConstraint(
            "upper_bound IS NULL OR upper_bound >= 0",
            name="ck_forecasts_upper_bound_non_negative",
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 100)",
            name="ck_forecasts_confidence_range",
        ),
        CheckConstraint("mape IS NULL OR mape >= 0", name="ck_forecasts_mape_non_negative"),
        CheckConstraint("rmse IS NULL OR rmse >= 0", name="ck_forecasts_rmse_non_negative"),
        Index("ix_forecasts_product_period", "product_id", "period"),
        Index("ix_forecasts_model_period", "model_type", "period"),
    )

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    model_type = Column(String(50), nullable=False)
    period = Column(Date, nullable=False, index=True)
    predicted_qty = Column(Numeric(12, 2), nullable=False)
    lower_bound = Column(Numeric(12, 2), nullable=True)
    upper_bound = Column(Numeric(12, 2), nullable=True)
    confidence = Column(Numeric(5, 2), nullable=True)
    mape = Column(Numeric(8, 4), nullable=True)
    rmse = Column(Numeric(12, 4), nullable=True)
    features_used = Column(Text, nullable=True)
    model_version = Column(String(50), nullable=True)
    training_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
