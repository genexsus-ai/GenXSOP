from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class CategoryBase(BaseModel):
    name: str
    parent_id: Optional[int] = None
    level: int = 0
    description: Optional[str] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryResponse(CategoryBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ProductBase(BaseModel):
    sku: str
    name: str
    description: Optional[str] = None
    category_id: Optional[int] = None
    product_family: Optional[str] = None
    unit_of_measure: str = "units"
    unit_cost: Optional[Decimal] = None
    selling_price: Optional[Decimal] = None
    lead_time_days: int = 0
    min_order_qty: int = 1
    status: str = "active"


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    product_family: Optional[str] = None
    unit_of_measure: Optional[str] = None
    unit_cost: Optional[Decimal] = None
    selling_price: Optional[Decimal] = None
    lead_time_days: Optional[int] = None
    min_order_qty: Optional[int] = None
    status: Optional[str] = None


class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    items: List[ProductResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
