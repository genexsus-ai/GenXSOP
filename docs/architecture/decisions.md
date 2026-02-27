# Architecture Decisions (Lightweight)

This is a lightweight record of the key architectural decisions evident in the current codebase.

> If you want formal ADRs, we can split these into separate files under `docs/adr/`.

## Decision 1 — Layered backend (Router → Service → Repository)

**Status:** Adopted

**Why:** Keep HTTP concerns separate from business rules and persistence.

**Where in code:**

- Routers: `backend/app/routers/*`
- Services: `backend/app/services/*`
- Repositories: `backend/app/repositories/*`

## Decision 2 — Domain exceptions + global exception handler

**Status:** Adopted

**Why:** Consistent error responses and thin routers.

**Where in code:**

- Exceptions: `backend/app/core/exceptions.py`
- Handler: `backend/app/main.py`

## Decision 3 — Forecasting extensibility via Strategy + Factory

**Status:** Adopted

**Why:** Add/replace forecasting algorithms without changing service/router code.

**Where in code:**

- Strategies: `backend/app/ml/strategies.py`
- Factory: `backend/app/ml/factory.py`
- Service usage: `backend/app/services/forecast_service.py`

## Decision 4 — EventBus for audit logging (Observer)

**Status:** Adopted

**Why:** Audit log and other side effects should be decoupled from core write logic.

**Where in code:**

- EventBus: `backend/app/utils/events.py`
- Startup config: `backend/app/main.py`

## Decision 5 — Frontend API access via Axios interceptors

**Status:** Adopted

**Why:** Centralize auth header injection and common error behavior.

**Where in code:**

- `frontend/src/services/api.ts`
