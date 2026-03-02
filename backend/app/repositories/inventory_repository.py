"""
Inventory Repository — Repository Pattern (GoF)
"""
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from app.repositories.base import BaseRepository
from app.models.inventory import Inventory


class InventoryRepository(BaseRepository[Inventory]):

    def __init__(self, db: Session):
        super().__init__(Inventory, db)

    def list_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        product_id: Optional[int] = None,
        location: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Tuple[List[Inventory], int]:
        q = self.db.query(Inventory)
        if product_id:
            q = q.filter(Inventory.product_id == product_id)
        if location:
            q = q.filter(Inventory.location == location)
        if status:
            q = q.filter(Inventory.status == status)
        total = q.count()
        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def get_by_product_and_location(self, product_id: int, location: str) -> Optional[Inventory]:
        return (
            self.db.query(Inventory)
            .filter(Inventory.product_id == product_id, Inventory.location == location)
            .first()
        )

    def get_by_status(self, status: str) -> List[Inventory]:
        return self.db.query(Inventory).filter(Inventory.status == status).all()

    def get_critical(self) -> List[Inventory]:
        return self.get_by_status("critical")

    def get_low(self) -> List[Inventory]:
        return self.get_by_status("low")

    def get_excess(self) -> List[Inventory]:
        return self.get_by_status("excess")

    def get_all_inventory(self) -> List[Inventory]:
        return self.db.query(Inventory).all()

    def list_for_policy(
        self,
        product_id: Optional[int] = None,
        location: Optional[str] = None,
    ) -> List[Inventory]:
        q = self.db.query(Inventory)
        if product_id:
            q = q.filter(Inventory.product_id == product_id)
        if location:
            q = q.filter(Inventory.location == location)
        return q.all()
