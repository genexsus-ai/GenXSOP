from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    DateTime,
    ForeignKey,
    Text,
    CheckConstraint,
    Index,
    func,
)

from app.database import Base


class AgenticScheduleRecommendation(Base):
    __tablename__ = "agentic_schedule_recommendations"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('MACHINE_DOWN', 'MACHINE_RECOVERED', 'ORDER_PRIORITY_CHANGED', "
            "'MATERIAL_SHORTAGE', 'QUALITY_HOLD', 'QUALITY_RELEASED', 'LABOR_UNAVAILABLE')",
            name="ck_agentic_sched_rec_event_type",
        ),
        CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="ck_agentic_sched_rec_severity",
        ),
        CheckConstraint(
            "state IN ('RECEIVED', 'CLASSIFIED', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED')",
            name="ck_agentic_sched_rec_state",
        ),
        CheckConstraint(
            "status IN ('pending_approval', 'approved', 'rejected')",
            name="ck_agentic_sched_rec_status",
        ),
        Index("ix_agentic_sched_rec_status_created", "status", "created_at"),
        Index("ix_agentic_sched_rec_supply_plan_status", "supply_plan_id", "status"),
        Index("ix_agentic_sched_rec_product_period", "product_id", "period"),
    )

    id = Column(Integer, primary_key=True, index=True)
    recommendation_id = Column(String(64), nullable=False, unique=True, index=True)
    workflow_id = Column(String(64), nullable=False, unique=True, index=True)

    event_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False, default="medium")
    event_timestamp = Column(DateTime, nullable=False)

    supply_plan_id = Column(Integer, ForeignKey("supply_plans.id"), nullable=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True, index=True)
    period = Column(Date, nullable=True, index=True)
    workcenter = Column(String(100), nullable=True)
    line = Column(String(100), nullable=True)
    shift = Column(String(50), nullable=True)

    impacted_rows = Column(Integer, nullable=False, default=0)
    recommendation_summary = Column(Text, nullable=False)
    explanation = Column(Text, nullable=False)
    actions_json = Column(Text, nullable=False)

    state = Column(String(30), nullable=False, default="PENDING_APPROVAL")
    status = Column(String(30), nullable=False, default="pending_approval")
    decision_note = Column(Text, nullable=True)
    decided_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    decided_at = Column(DateTime, nullable=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
