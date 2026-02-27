# Cross-cutting Concerns

This document captures non-functional and cross-cutting concerns that apply across modules.

## Security

### Authentication

- JWT Bearer tokens.
- Backend issues tokens in `POST /api/v1/auth/login`.
- Backend validates tokens via `dependencies.get_current_user()`.

### Authorization (RBAC)

- Implemented via dependency `require_roles([...])`.
- Routers declare required roles at the endpoint boundary.

### CORS

- Enabled in `backend/app/main.py`.
- Origins come from `settings.CORS_ORIGINS`.

## Error handling

- Domain exceptions extend `GenXSOPException` (`backend/app/core/exceptions.py`).
- Global exception handler in `backend/app/main.py` converts them to:

```json
{ "success": false, "error": { "code": "...", "message": "..." } }
```

- Frontend Axios response interceptor shows toast messages on common failures.

## Audit logging (Observer pattern)

- Services publish domain events to `EventBus` (`backend/app/utils/events.py`).
- `AuditLogHandler` persists to `audit_logs`.
- This keeps audit concerns out of routers/services.

## Testing

Backend:

- `pytest`
- Unit tests: `backend/tests/unit/*`
- Integration tests: `backend/tests/integration/*`

Frontend:

- `vitest` (`npm run test`)

## Performance

- API calls are synchronous; forecast generation is in-process and may be CPU heavy.
- Consider background jobs for long forecasts and/or caching dashboard aggregates.

## Observability (current)

- Logging via Python `logging`.
- EventBus includes `LoggingHandler` for domain event visibility.

## Data integrity

- SQLAlchemy ORM models define basic columns and foreign keys.
- Some constraints described in the design doc (uniqueness across product/period/version) are not explicitly defined in models; consider adding them in Alembic migrations.
