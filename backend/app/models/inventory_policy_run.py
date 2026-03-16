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


class InventoryPolicyRun(Base):
    """Tracks each inventory optimization execution (enterprise audit + operations).

    This is intentionally similar to ForecastJob to provide:
    - run history (who/when/what scope)
    - operational status (running/completed/failed)
    - replay/debug metadata (parameters + results summary)
    """

    __tablename__ = "inventory_policy_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'completed', 'failed')",
            name="ck_inventory_policy_runs_status",
        ),
        Index("ix_inventory_policy_runs_status_created", "status", "created_at"),
        Index("ix_inventory_policy_runs_requested_by_created", "requested_by", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(64), unique=True, index=True, nullable=False)
    status = Column(String(20), nullable=False, index=True)

    # Optional scope filters used for the run.
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True, index=True)
    location = Column(String(100), nullable=True, index=True)

    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    parameters_json = Column(Text, nullable=True)
    result_json = Column(Text, nullable=True)
    error = Column(Text, nullable=True)

    processed_count = Column(Integer, nullable=False, default=0)
    updated_count = Column(Integer, nullable=False, default=0)
    exception_count = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, default=func.now(), nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
