"""
Event / Observer Pattern — GoF Observer Pattern

Principles applied:
- Observer Pattern (GoF): Publishers emit events; subscribers react without tight coupling.
- Single Responsibility Principle (SRP): Each handler has one job (e.g., write audit log).
- Open/Closed Principle (OCP): Add new event handlers without modifying the publisher.
- Dependency Inversion Principle (DIP): Publishers depend on the abstract EventBus, not concrete handlers.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Type
import logging

logger = logging.getLogger(__name__)


# ── Domain Events ─────────────────────────────────────────────────────────────

@dataclass
class DomainEvent:
    """Base class for all domain events."""
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    user_id: Optional[int] = None


@dataclass
class EntityCreatedEvent(DomainEvent):
    entity_type: str = ""
    entity_id: int = 0
    new_values: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EntityUpdatedEvent(DomainEvent):
    entity_type: str = ""
    entity_id: int = 0
    old_values: Dict[str, Any] = field(default_factory=dict)
    new_values: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EntityDeletedEvent(DomainEvent):
    entity_type: str = ""
    entity_id: int = 0


@dataclass
class PlanStatusChangedEvent(DomainEvent):
    entity_type: str = ""
    entity_id: int = 0
    old_status: str = ""
    new_status: str = ""
    comment: Optional[str] = None


@dataclass
class ForecastGeneratedEvent(DomainEvent):
    product_id: int = 0
    model_type: str = ""
    horizon_months: int = 0
    records_created: int = 0


# ── Abstract Observer ─────────────────────────────────────────────────────────

class EventHandler(ABC):
    """Abstract observer. Concrete handlers implement `handle()`."""

    @abstractmethod
    def handle(self, event: DomainEvent) -> None:
        ...

    def can_handle(self, event: DomainEvent) -> bool:
        """Override to filter which event types this handler processes."""
        return True


# ── Concrete Observers ────────────────────────────────────────────────────────

class AuditLogHandler(EventHandler):
    """
    Writes audit log entries to the database.
    Observes all entity mutation events.
    """

    def __init__(self, db_session_factory: Callable):
        self._db_factory = db_session_factory

    def handle(self, event: DomainEvent) -> None:
        from app.models.comment import AuditLog
        try:
            import json
            db = self._db_factory()
            action = self._resolve_action(event)
            entity_type = getattr(event, "entity_type", "unknown")
            entity_id = getattr(event, "entity_id", 0)
            old_values = json.dumps(getattr(event, "old_values", None))
            new_values = json.dumps(getattr(event, "new_values", None))
            log = AuditLog(
                user_id=event.user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                old_values=old_values,
                new_values=new_values,
            )
            db.add(log)
            db.commit()
        except Exception as exc:
            logger.warning("AuditLogHandler failed: %s", exc)

    def _resolve_action(self, event: DomainEvent) -> str:
        if isinstance(event, EntityCreatedEvent):
            return "create"
        if isinstance(event, EntityUpdatedEvent):
            return "update"
        if isinstance(event, EntityDeletedEvent):
            return "delete"
        if isinstance(event, PlanStatusChangedEvent):
            return f"status_change:{event.old_status}->{event.new_status}"
        if isinstance(event, ForecastGeneratedEvent):
            return "forecast_generated"
        return "unknown"


class LoggingHandler(EventHandler):
    """
    Lightweight observer that logs events to the application logger.
    Useful for debugging and monitoring.
    """

    def handle(self, event: DomainEvent) -> None:
        logger.info(
            "[EVENT] %s | user=%s | entity=%s id=%s",
            type(event).__name__,
            event.user_id,
            getattr(event, "entity_type", "N/A"),
            getattr(event, "entity_id", "N/A"),
        )


# ── Event Bus (Publisher) ─────────────────────────────────────────────────────

class EventBus:
    """
    Central event bus — the Subject in the Observer pattern.
    Publishers emit events; registered handlers are notified automatically.

    Usage:
        bus = EventBus()
        bus.subscribe(AuditLogHandler(db_factory))
        bus.publish(EntityCreatedEvent(entity_type="demand_plan", entity_id=1, user_id=5))
    """

    def __init__(self):
        self._handlers: List[EventHandler] = []

    def subscribe(self, handler: EventHandler) -> None:
        """Register an observer."""
        self._handlers.append(handler)

    def unsubscribe(self, handler: EventHandler) -> None:
        """Remove an observer."""
        self._handlers = [h for h in self._handlers if h is not handler]

    def publish(self, event: DomainEvent) -> None:
        """Notify all registered observers of the event."""
        for handler in self._handlers:
            try:
                if handler.can_handle(event):
                    handler.handle(event)
            except Exception as exc:
                logger.error("EventBus handler %s failed: %s", type(handler).__name__, exc)


# ── Singleton Event Bus ───────────────────────────────────────────────────────

_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """
    Return the application-level singleton EventBus.
    Initialized once in main.py startup.
    """
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
        _event_bus.subscribe(LoggingHandler())
    return _event_bus


def configure_event_bus(db_session_factory: Callable) -> EventBus:
    """
    Configure the event bus with all production handlers.
    Called once during application startup.
    """
    global _event_bus
    _event_bus = EventBus()
    _event_bus.subscribe(LoggingHandler())
    _event_bus.subscribe(AuditLogHandler(db_session_factory))
    return _event_bus
