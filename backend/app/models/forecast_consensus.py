from sqlalchemy import (
    Column,
    Integer,
    Numeric,
    Date,
    DateTime,
    String,
    Text,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Index,
    func,
)
from app.database import Base


class ForecastConsensus(Base):
    __tablename__ = "forecast_consensus"
    __table_args__ = (
        UniqueConstraint(
            "forecast_run_audit_id",
            "period",
            "version",
            name="uq_forecast_consensus_run_period_version",
        ),
        CheckConstraint("baseline_qty >= 0", name="ck_forecast_consensus_baseline_non_negative"),
        CheckConstraint(
            "constraint_cap_qty IS NULL OR constraint_cap_qty >= 0",
            name="ck_forecast_consensus_cap_non_negative",
        ),
        CheckConstraint("pre_consensus_qty >= 0", name="ck_forecast_consensus_pre_non_negative"),
        CheckConstraint("final_consensus_qty >= 0", name="ck_forecast_consensus_final_non_negative"),
        CheckConstraint(
            "status IN ('draft', 'proposed', 'approved', 'frozen')",
            name="ck_forecast_consensus_status",
        ),
        CheckConstraint("version >= 1", name="ck_forecast_consensus_version_min_1"),
        Index("ix_forecast_consensus_run_period", "forecast_run_audit_id", "period"),
        Index("ix_forecast_consensus_product_period", "product_id", "period"),
        Index("ix_forecast_consensus_status_period", "status", "period"),
    )

    id = Column(Integer, primary_key=True, index=True)
    forecast_run_audit_id = Column(
        Integer,
        ForeignKey("forecast_run_audits.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    period = Column(Date, nullable=False, index=True)

    baseline_qty = Column(Numeric(12, 2), nullable=False)
    sales_override_qty = Column(Numeric(12, 2), nullable=False, default=0)
    marketing_uplift_qty = Column(Numeric(12, 2), nullable=False, default=0)
    finance_adjustment_qty = Column(Numeric(12, 2), nullable=False, default=0)
    constraint_cap_qty = Column(Numeric(12, 2), nullable=True)

    pre_consensus_qty = Column(Numeric(12, 2), nullable=False)
    final_consensus_qty = Column(Numeric(12, 2), nullable=False)

    status = Column(String(20), nullable=False, default="draft")
    notes = Column(Text, nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)

    version = Column(Integer, nullable=False, default=1)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
