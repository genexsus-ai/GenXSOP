from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    Date,
    DateTime,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    Index,
    func,
)
from app.database import Base


class ProductionSchedule(Base):
    __tablename__ = "production_schedules"
    __table_args__ = (
        UniqueConstraint(
            "supply_plan_id",
            "workcenter",
            "line",
            "shift",
            "sequence_order",
            name="uq_production_schedule_slot_sequence",
        ),
        CheckConstraint("planned_qty >= 0", name="ck_production_schedules_planned_qty_non_negative"),
        CheckConstraint("sequence_order >= 1", name="ck_production_schedules_sequence_min_1"),
        CheckConstraint(
            "status IN ('draft', 'released', 'in_progress', 'completed')",
            name="ck_production_schedules_status",
        ),
        Index("ix_production_schedules_product_period", "product_id", "period"),
        Index("ix_production_schedules_workcenter_line_shift", "workcenter", "line", "shift"),
    )

    id = Column(Integer, primary_key=True, index=True)
    supply_plan_id = Column(Integer, ForeignKey("supply_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    period = Column(Date, nullable=False, index=True)

    workcenter = Column(String(100), nullable=False, default="WC-1")
    line = Column(String(100), nullable=False, default="Line-1")
    shift = Column(String(50), nullable=False, default="Shift-A")
    sequence_order = Column(Integer, nullable=False, default=1)

    planned_qty = Column(Numeric(12, 2), nullable=False, default=0)
    planned_start_at = Column(DateTime, nullable=False)
    planned_end_at = Column(DateTime, nullable=False)

    status = Column(String(20), nullable=False, default="draft")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
