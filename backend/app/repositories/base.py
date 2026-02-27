"""
Base Repository — Repository Pattern (GoF)

Principles applied:
- Single Responsibility Principle (SRP): Only handles data access for one model type.
- Open/Closed Principle (OCP): Extend by subclassing, not modifying.
- Liskov Substitution Principle (LSP): All concrete repos are substitutable for BaseRepository.
- Dependency Inversion Principle (DIP): Routers/services depend on this abstraction, not SQLAlchemy directly.
"""
from typing import Generic, TypeVar, Type, Optional, List, Any, Dict
from sqlalchemy.orm import Session
from app.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Generic CRUD repository.
    Concrete repositories inherit this and add domain-specific query methods.
    """

    def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db

    # ── Read ─────────────────────────────────────────────────────────────────

    def get_by_id(self, entity_id: int) -> Optional[ModelType]:
        """Fetch a single record by primary key."""
        return self.db.query(self.model).filter(self.model.id == entity_id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Fetch all records with optional pagination."""
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def count(self) -> int:
        """Return total count of records."""
        return self.db.query(self.model).count()

    def exists(self, entity_id: int) -> bool:
        """Check if a record exists by primary key."""
        return self.db.query(self.model).filter(self.model.id == entity_id).first() is not None

    # ── Write ────────────────────────────────────────────────────────────────

    def create(self, obj: ModelType) -> ModelType:
        """Persist a new entity to the database."""
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, obj: ModelType, updates: Dict[str, Any]) -> ModelType:
        """Apply a dict of field updates to an existing entity."""
        for field, value in updates.items():
            if hasattr(obj, field):
                setattr(obj, field, value)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, obj: ModelType) -> None:
        """Hard-delete an entity from the database."""
        self.db.delete(obj)
        self.db.commit()

    def save(self) -> None:
        """Flush and commit the current session."""
        self.db.commit()

    def refresh(self, obj: ModelType) -> ModelType:
        """Refresh an entity from the database."""
        self.db.refresh(obj)
        return obj
