from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    CheckConstraint,
    Index,
    func,
)

from app.database import Base


class ProductionEvent(Base):
    __tablename__ = "production_events"
    __table_args__ = (
        CheckConstraint(
            "event_source IN ('ERP', 'MES', 'IIOT', 'QMS', 'CMMS', 'MANUAL')",
            name="ck_production_events_source",
        ),
        CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="ck_production_events_severity",
        ),
        CheckConstraint(
            "processing_status IN ('RECEIVED', 'NORMALIZED', 'PROCESSED', 'FAILED', 'REPLAYED')",
            name="ck_production_events_processing_status",
        ),
        Index("ix_production_events_source_ts", "event_source", "event_timestamp"),
        Index("ix_production_events_correlation", "correlation_id"),
        Index("ix_production_events_trace", "trace_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(64), nullable=False, unique=True, index=True)
    event_type = Column(String(80), nullable=False, index=True)
    event_source = Column(String(20), nullable=False, index=True)
    event_timestamp = Column(DateTime, nullable=False, index=True)

    plant_id = Column(String(64), nullable=True, index=True)
    line_id = Column(String(64), nullable=True, index=True)
    resource_id = Column(String(64), nullable=True, index=True)
    order_id = Column(String(64), nullable=True, index=True)
    severity = Column(String(20), nullable=False, default="medium")

    payload_json = Column(Text, nullable=False)
    normalized_json = Column(Text, nullable=True)

    correlation_id = Column(String(128), nullable=True)
    trace_id = Column(String(128), nullable=True)
    idempotency_key = Column(String(128), nullable=True, unique=True, index=True)
    duplicate_of_event_id = Column(String(64), nullable=True)

    processing_status = Column(String(20), nullable=False, default="RECEIVED")
    replay_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)

    received_at = Column(DateTime, nullable=False, default=func.now())
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
