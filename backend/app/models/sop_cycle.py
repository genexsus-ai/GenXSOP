from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Text, func
from app.database import Base


class SOPCycle(Base):
    __tablename__ = "sop_cycles"

    id = Column(Integer, primary_key=True, index=True)
    cycle_name = Column(String(255), nullable=False)
    period = Column(Date, nullable=False)
    current_step = Column(Integer, default=1)
    step_1_status = Column(String(20), default="pending")
    step_1_due_date = Column(Date, nullable=True)
    step_1_owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    step_2_status = Column(String(20), default="pending")
    step_2_due_date = Column(Date, nullable=True)
    step_2_owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    step_3_status = Column(String(20), default="pending")
    step_3_due_date = Column(Date, nullable=True)
    step_3_owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    step_4_status = Column(String(20), default="pending")
    step_4_due_date = Column(Date, nullable=True)
    step_4_owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    step_5_status = Column(String(20), default="pending")
    step_5_due_date = Column(Date, nullable=True)
    step_5_owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    decisions = Column(Text, nullable=True)
    action_items = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    overall_status = Column(String(20), default="active")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
