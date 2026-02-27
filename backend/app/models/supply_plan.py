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


class SupplyPlan(Base):
    __tablename__ = "supply_plans"
    __table_args__ = (
        UniqueConstraint(
            "product_id",
            "period",
            "location",
            "version",
            name="uq_supply_plans_business_key",
        ),
        CheckConstraint(
            "status IN ('draft', 'submitted', 'approved')",
            name="ck_supply_plans_status",
        ),
        CheckConstraint(
            "planned_prod_qty IS NULL OR planned_prod_qty >= 0",
            name="ck_supply_plans_planned_qty_non_negative",
        ),
        CheckConstraint(
            "actual_prod_qty IS NULL OR actual_prod_qty >= 0",
            name="ck_supply_plans_actual_qty_non_negative",
        ),
        CheckConstraint(
            "capacity_max IS NULL OR capacity_max >= 0",
            name="ck_supply_plans_capacity_max_non_negative",
        ),
        CheckConstraint(
            "capacity_used IS NULL OR (capacity_used >= 0 AND capacity_used <= 100)",
            name="ck_supply_plans_capacity_used_range",
        ),
        CheckConstraint(
            "lead_time_days IS NULL OR lead_time_days >= 0",
            name="ck_supply_plans_lead_time_non_negative",
        ),
        CheckConstraint(
            "cost_per_unit IS NULL OR cost_per_unit >= 0",
            name="ck_supply_plans_cost_per_unit_non_negative",
        ),
        CheckConstraint("version >= 1", name="ck_supply_plans_version_min_1"),
        Index("ix_supply_plans_status_period", "status", "period"),
        Index("ix_supply_plans_product_period", "product_id", "period"),
    )

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    period = Column(Date, nullable=False, index=True)
    location = Column(String(100), default="Main")
    planned_prod_qty = Column(Numeric(12, 2), nullable=True)
    actual_prod_qty = Column(Numeric(12, 2), nullable=True)
    capacity_max = Column(Numeric(12, 2), nullable=True)
    capacity_used = Column(Numeric(5, 2), nullable=True)
    supplier_name = Column(String(255), nullable=True)
    lead_time_days = Column(Integer, nullable=True)
    cost_per_unit = Column(Numeric(12, 2), nullable=True)
    constraints = Column(Text, nullable=True)
    status = Column(String(20), default="draft")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
