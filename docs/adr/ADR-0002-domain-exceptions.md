# ADR-0002: Domain exceptions + global exception handler

**Status:** Accepted

## Context

Without a consistent approach, each router would need to catch errors and map them to HTTP responses. This leads to:

- duplicated error handling,
- inconsistent error payloads,
- routers mixing domain logic and HTTP logic.

## Decision

Implement a domain exception hierarchy and a single global exception handler:

- Domain exceptions extend `GenXSOPException` (`backend/app/core/exceptions.py`).
- `backend/app/main.py` registers an exception handler for `GenXSOPException`.
- The handler maps a domain error code to an HTTP status and returns structured JSON.

## Consequences

### Positive

- Consistent error shape across endpoints.
- Routers remain thin.
- New domain errors can be added without rewriting router code.

### Negative

- Some services currently convert domain exceptions into FastAPI `HTTPException` early (via `to_http_exception(...)`). Ideally, services would only raise domain exceptions and let the global handler convert them.

## References

- `backend/app/core/exceptions.py`
- `backend/app/main.py`
