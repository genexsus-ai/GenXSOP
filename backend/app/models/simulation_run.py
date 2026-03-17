from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    CheckConstraint,
    Index,
    func,
)

from app.database import Base


class SimulationRun(Base):
    __tablename__ = "simulation_runs"
    __table_args__ = (
        CheckConstraint("status IN ('completed', 'failed')", name="ck_simulation_runs_status"),
        Index("ix_simulation_runs_status_created", "status", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    simulation_id = Column(String(64), nullable=False, unique=True, index=True)
    recommendation_id = Column(String(64), ForeignKey("agentic_schedule_recommendations.recommendation_id"), nullable=True, index=True)
    scenario_name = Column(String(120), nullable=True)

    status = Column(String(20), nullable=False, default="completed")
    request_json = Column(Text, nullable=True)
    result_json = Column(Text, nullable=True)
    error = Column(Text, nullable=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    completed_at = Column(DateTime, default=func.now(), nullable=False)
