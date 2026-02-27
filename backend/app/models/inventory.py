from sqlalchemy import Column, Integer, String, Numeric, DateTime, Date, ForeignKey, func
from app.database import Base


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    location = Column(String(100), default="Main")
    on_hand_qty = Column(Numeric(12, 2), default=0)
    allocated_qty = Column(Numeric(12, 2), default=0)
    in_transit_qty = Column(Numeric(12, 2), default=0)
    safety_stock = Column(Numeric(12, 2), default=0)
    reorder_point = Column(Numeric(12, 2), default=0)
    max_stock = Column(Numeric(12, 2), nullable=True)
    days_of_supply = Column(Numeric(8, 2), nullable=True)
    last_receipt_date = Column(Date, nullable=True)
    last_issue_date = Column(Date, nullable=True)
    valuation = Column(Numeric(14, 2), nullable=True)
    status = Column(String(20), default="normal")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
