from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    Numeric,
    CheckConstraint,
    Index,
    func,
)
from app.database import Base


class InventoryPolicyRecommendation(Base):
    __tablename__ = "inventory_policy_recommendations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected', 'applied')",
            name="ck_inventory_policy_recommendation_status",
        ),
        CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 1",
            name="ck_inventory_policy_recommendation_confidence_range",
        ),
        Index("ix_inventory_policy_recommendations_status_created", "status", "created_at"),
        Index("ix_inventory_policy_recommendations_inventory_status", "inventory_id", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    inventory_id = Column(Integer, ForeignKey("inventory.id"), nullable=False, index=True)
    recommended_safety_stock = Column(Numeric(12, 2), nullable=False)
    recommended_reorder_point = Column(Numeric(12, 2), nullable=False)
    recommended_max_stock = Column(Numeric(12, 2), nullable=True)
    confidence_score = Column(Numeric(5, 4), nullable=False, default=0.70)
    rationale = Column(Text, nullable=False)
    signals_json = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    decision_notes = Column(Text, nullable=True)
    decided_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    decided_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
