# ADR-0005: Axios interceptors for auth + error handling

**Status:** Accepted

## Context

The SPA makes many API calls across modules. We need a consistent mechanism to:

- attach the JWT access token,
- handle common errors (401/403/422/500),
- keep page code focused on UI logic.

## Decision

Create a shared Axios instance with interceptors:

- Request interceptor reads `access_token` from `localStorage` and sets `Authorization: Bearer <token>`.
- Response interceptor:
  - on 401 → clear token and redirect to `/login`
  - on 403/422/500 → show toast notifications

## Consequences

### Positive

- Centralized, consistent behavior for all API calls.
- Less duplicated error handling in pages.

### Negative

- Token storage is split between Zustand and localStorage.
- Redirect-on-401 is a blunt instrument; a refresh-token flow would be more user-friendly.

## References

- `frontend/src/services/api.ts`
- `frontend/src/store/authStore.ts`
