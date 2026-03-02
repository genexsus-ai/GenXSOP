from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Date,
    ForeignKey,
    Text,
    CheckConstraint,
    Index,
    func,
)
from app.database import Base


class InventoryPolicyException(Base):
    __tablename__ = "inventory_policy_exceptions"
    __table_args__ = (
        CheckConstraint(
            "exception_type IN ('stockout_risk', 'excess_risk', 'data_quality_risk')",
            name="ck_inventory_policy_exception_type",
        ),
        CheckConstraint(
            "severity IN ('low', 'medium', 'high')",
            name="ck_inventory_policy_exception_severity",
        ),
        CheckConstraint(
            "status IN ('open', 'in_progress', 'resolved', 'dismissed')",
            name="ck_inventory_policy_exception_status",
        ),
        Index("ix_inventory_policy_exceptions_status_due", "status", "due_date"),
        Index("ix_inventory_policy_exceptions_inventory_type", "inventory_id", "exception_type"),
    )

    id = Column(Integer, primary_key=True, index=True)
    inventory_id = Column(Integer, ForeignKey("inventory.id"), nullable=False, index=True)
    exception_type = Column(String(30), nullable=False)
    severity = Column(String(10), nullable=False, default="medium")
    status = Column(String(20), nullable=False, default="open")
    recommended_action = Column(Text, nullable=False)
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    due_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
