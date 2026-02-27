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


class DemandPlan(Base):
    __tablename__ = "demand_plans"
    __table_args__ = (
        UniqueConstraint(
            "product_id",
            "period",
            "region",
            "channel",
            "version",
            name="uq_demand_plans_business_key",
        ),
        CheckConstraint(
            "status IN ('draft', 'submitted', 'approved')",
            name="ck_demand_plans_status",
        ),
        CheckConstraint("forecast_qty >= 0", name="ck_demand_plans_forecast_qty_non_negative"),
        CheckConstraint("adjusted_qty IS NULL OR adjusted_qty >= 0", name="ck_demand_plans_adjusted_qty_non_negative"),
        CheckConstraint("actual_qty IS NULL OR actual_qty >= 0", name="ck_demand_plans_actual_qty_non_negative"),
        CheckConstraint("consensus_qty IS NULL OR consensus_qty >= 0", name="ck_demand_plans_consensus_qty_non_negative"),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 100)",
            name="ck_demand_plans_confidence_range",
        ),
        CheckConstraint("version >= 1", name="ck_demand_plans_version_min_1"),
        Index("ix_demand_plans_status_period", "status", "period"),
        Index("ix_demand_plans_product_period", "product_id", "period"),
    )

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    period = Column(Date, nullable=False, index=True)
    region = Column(String(100), default="Global")
    channel = Column(String(100), default="All")
    forecast_qty = Column(Numeric(12, 2), nullable=False)
    adjusted_qty = Column(Numeric(12, 2), nullable=True)
    actual_qty = Column(Numeric(12, 2), nullable=True)
    consensus_qty = Column(Numeric(12, 2), nullable=True)
    confidence = Column(Numeric(5, 2), nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String(20), default="draft")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
