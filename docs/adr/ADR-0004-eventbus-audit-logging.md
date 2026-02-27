# ADR-0004: EventBus (Observer) for audit logging

**Status:** Accepted

## Context

The platform needs an audit trail (who changed what and when) without forcing every service method to write audit rows directly.

We also want to enable future side effects like:

- notifications,
- activity feeds,
- analytics events.

## Decision

Introduce an in-process **EventBus** (Observer Pattern):

- Services publish domain events (`EntityCreatedEvent`, `EntityUpdatedEvent`, etc.)
- Handlers subscribe and react
- `AuditLogHandler` writes to the `audit_logs` table
- `LoggingHandler` writes to app logs

The EventBus is configured once at startup:

- `configure_event_bus(db_session_factory=SessionLocal)` called in `backend/app/main.py`

## Consequences

### Positive

- Cross-cutting behaviors are decoupled from core business logic.
- Easy to add new handlers without modifying existing publishers.

### Negative

- In-process event handling is not durable (if the process crashes mid-flight).
- Handlers that write to the DB can fail independently; we currently log warnings rather than fail the request.
- Long-running handlers would block the request; background queues may be required later.

## References

- `backend/app/utils/events.py`
- `backend/app/main.py`
- `backend/app/models/comment.py` (AuditLog model)
