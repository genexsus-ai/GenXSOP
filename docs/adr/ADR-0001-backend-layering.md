# ADR-0001: Backend layering (Router → Service → Repository)

**Status:** Accepted

## Context

GenXSOP has multiple domains (demand, supply, inventory, forecasting, scenarios, S&OP cycles, KPI). We need a structure that:

- keeps HTTP concerns isolated from business rules,
- keeps persistence concerns isolated from business rules,
- supports unit testing without hitting HTTP or the database for all tests.

## Decision

Use a layered architecture in the FastAPI backend:

- **Router** layer (`backend/app/routers/*`) is a thin HTTP controller
- **Service** layer (`backend/app/services/*`) owns business logic and orchestration
- **Repository** layer (`backend/app/repositories/*`) owns database queries and persistence

Dependency direction is one-way:

`router → service → repository → SQLAlchemy models`

## Consequences

### Positive

- Improves separation of concerns and readability.
- Services can be tested with a test database or mocked repositories.
- Routers stay small and consistent.

### Negative

- More files and boilerplate.
- Requires discipline to avoid bypassing the service/repository layers.

## References

- `backend/app/routers/forecasting.py`
- `backend/app/services/forecast_service.py`
- `backend/app/repositories/base.py`
