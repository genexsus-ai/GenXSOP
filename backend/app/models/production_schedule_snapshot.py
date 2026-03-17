from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
    Index,
    func,
)

from app.database import Base


class ProductionScheduleSnapshot(Base):
    __tablename__ = "production_schedule_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "supply_plan_id",
            "version_number",
            name="uq_schedule_snapshot_supply_plan_version",
        ),
        Index("ix_schedule_snapshot_supply_plan", "supply_plan_id"),
        Index("ix_schedule_snapshot_recommendation", "recommendation_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    supply_plan_id = Column(Integer, ForeignKey("supply_plans.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    recommendation_id = Column(String(64), nullable=True)

    snapshot_json = Column(Text, nullable=False)

    published_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    published_at = Column(DateTime, nullable=False, default=func.now())
    created_at = Column(DateTime, nullable=False, default=func.now())
