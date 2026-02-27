from sqlalchemy import Column, Integer, String, Numeric, DateTime, Date, ForeignKey, Text, func
from app.database import Base


class DemandPlan(Base):
    __tablename__ = "demand_plans"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    period = Column(Date, nullable=False, index=True)
    region = Column(String(100), default="Global")
    channel = Column(String(100), default="All")
    forecast_qty = Column(Numeric(12, 2), nullable=False)
    adjusted_qty = Column(Numeric(12, 2), nullable=True)
    actual_qty = Column(Numeric(12, 2), nullable=True)
    consensus_qty = Column(Numeric(12, 2), nullable=True)
    confidence = Column(Numeric(5, 2), nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String(20), default="draft")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
