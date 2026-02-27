from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    DateTime,
    Date,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    Index,
    func,
)
from app.database import Base


class Inventory(Base):
    __tablename__ = "inventory"
    __table_args__ = (
        UniqueConstraint("product_id", "location", name="uq_inventory_product_location"),
        CheckConstraint(
            "status IN ('normal', 'low', 'critical', 'excess')",
            name="ck_inventory_status",
        ),
        CheckConstraint("on_hand_qty >= 0", name="ck_inventory_on_hand_non_negative"),
        CheckConstraint("allocated_qty >= 0", name="ck_inventory_allocated_non_negative"),
        CheckConstraint("in_transit_qty >= 0", name="ck_inventory_in_transit_non_negative"),
        CheckConstraint("safety_stock >= 0", name="ck_inventory_safety_stock_non_negative"),
        CheckConstraint("reorder_point >= 0", name="ck_inventory_reorder_point_non_negative"),
        CheckConstraint("max_stock IS NULL OR max_stock >= 0", name="ck_inventory_max_stock_non_negative"),
        CheckConstraint(
            "days_of_supply IS NULL OR days_of_supply >= 0",
            name="ck_inventory_days_of_supply_non_negative",
        ),
        CheckConstraint("valuation IS NULL OR valuation >= 0", name="ck_inventory_valuation_non_negative"),
        Index("ix_inventory_status_location", "status", "location"),
    )

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
