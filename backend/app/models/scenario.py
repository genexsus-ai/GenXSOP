from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    DateTime,
    ForeignKey,
    Text,
    CheckConstraint,
    Index,
    func,
)
from app.database import Base


class Scenario(Base):
    __tablename__ = "scenarios"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'submitted', 'completed', 'approved', 'rejected')",
            name="ck_scenarios_status",
        ),
        CheckConstraint(
            "scenario_type IN ('what_if', 'baseline', 'stress_test')",
            name="ck_scenarios_type",
        ),
        Index("ix_scenarios_status_created_at", "status", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    scenario_type = Column(String(50), default="what_if")
    parameters = Column(Text, nullable=False, default="{}")
    base_demand_version = Column(Integer, nullable=True)
    base_supply_version = Column(Integer, nullable=True)
    results = Column(Text, nullable=True)
    revenue_impact = Column(Numeric(14, 2), nullable=True)
    margin_impact = Column(Numeric(14, 2), nullable=True)
    inventory_impact = Column(Numeric(14, 2), nullable=True)
    service_level_impact = Column(Numeric(5, 2), nullable=True)
    status = Column(String(20), default="draft")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
