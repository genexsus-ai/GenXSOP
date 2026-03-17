from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)

from app.database import Base


class AgenticSchedulingConfig(Base):
    __tablename__ = "agentic_scheduling_configs"
    __table_args__ = (
        UniqueConstraint("config_type", "scope", "name", name="uq_agentic_sched_cfg_type_scope_name"),
        CheckConstraint("config_type IN ('objectives', 'policies')", name="ck_agentic_sched_cfg_type"),
    )

    id = Column(Integer, primary_key=True, index=True)
    config_type = Column(String(20), nullable=False, index=True)
    scope = Column(String(30), nullable=False, default="global")
    name = Column(String(100), nullable=False, default="default")
    config_json = Column(Text, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, nullable=False, default=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
