from sqlalchemy import Column, Integer, String, Numeric, DateTime, Date, ForeignKey, Text, func
from app.database import Base


class SupplyPlan(Base):
    __tablename__ = "supply_plans"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    period = Column(Date, nullable=False, index=True)
    location = Column(String(100), default="Main")
    planned_prod_qty = Column(Numeric(12, 2), nullable=True)
    actual_prod_qty = Column(Numeric(12, 2), nullable=True)
    capacity_max = Column(Numeric(12, 2), nullable=True)
    capacity_used = Column(Numeric(5, 2), nullable=True)
    supplier_name = Column(String(255), nullable=True)
    lead_time_days = Column(Integer, nullable=True)
    cost_per_unit = Column(Numeric(12, 2), nullable=True)
    constraints = Column(Text, nullable=True)
    status = Column(String(20), default="draft")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
