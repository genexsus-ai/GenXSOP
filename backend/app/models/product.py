from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, func
from app.database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    level = Column(Integer, default=0)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=func.now())


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    product_family = Column(String(100), nullable=True)
    unit_of_measure = Column(String(20), default="units")
    unit_cost = Column(Numeric(12, 2), nullable=True)
    selling_price = Column(Numeric(12, 2), nullable=True)
    lead_time_days = Column(Integer, default=0)
    min_order_qty = Column(Integer, default=1)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
