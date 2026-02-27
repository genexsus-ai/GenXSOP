"""
Product Repository — Repository Pattern (GoF)
"""
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from app.repositories.base import BaseRepository
from app.models.product import Product, Category


class ProductRepository(BaseRepository[Product]):

    def __init__(self, db: Session):
        super().__init__(Product, db)

    def list_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        category_id: Optional[int] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[Product], int]:
        q = self.db.query(Product)
        if status:
            q = q.filter(Product.status == status)
        if category_id:
            q = q.filter(Product.category_id == category_id)
        if search:
            q = q.filter(
                Product.name.ilike(f"%{search}%") | Product.sku.ilike(f"%{search}%")
            )
        total = q.count()
        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def get_by_sku(self, sku: str) -> Optional[Product]:
        return self.db.query(Product).filter(Product.sku == sku).first()

    def get_active(self) -> List[Product]:
        return self.db.query(Product).filter(Product.status == "active").all()


class CategoryRepository(BaseRepository[Category]):

    def __init__(self, db: Session):
        super().__init__(Category, db)

    def get_all_categories(self) -> List[Category]:
        return self.db.query(Category).all()

    def get_by_name(self, name: str) -> Optional[Category]:
        return self.db.query(Category).filter(Category.name == name).first()
