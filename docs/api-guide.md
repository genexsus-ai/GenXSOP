# GenXSOP Developer / API Guide

This guide shows how to call the GenXSOP API directly (for integration, QA, or scripting).

## Postman (optional)

This repo includes ready-to-import Postman files:

- Collection: `docs/postman/GenXSOP.postman_collection.json`
- Environment: `docs/postman/GenXSOP.postman_environment.json`

### Import steps

1. Open Postman
2. **Import** → select the collection JSON
3. **Import** → select the environment JSON
4. Select the environment **“GenXSOP Local”** (top-right)
5. Run **Auth → Login (sets tokens)**

The login request will automatically save:

- `accessToken`
- `refreshToken`

Subsequent requests use `Authorization: Bearer {{accessToken}}`.

## Base URL

- Local: `http://localhost:8000/api/v1`
- Swagger UI: `http://localhost:8000/docs`

## Authentication

GenXSOP uses **JWT Bearer** authentication.

### 1) Login (get tokens)

```bash
curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"password"}'
```

Example response (shape):

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "user": { "id": 1, "email": "...", "role": "admin" }
}
```

### 2) Use the access token

```bash
TOKEN="<paste_access_token_here>"

curl -s "http://localhost:8000/api/v1/dashboard/summary" \
  -H "Authorization: Bearer $TOKEN"
```

### 3) Refresh token

```bash
curl -s -X POST "http://localhost:8000/api/v1/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<paste_refresh_token_here>"}'
```

### 4) Who am I?

```bash
curl -s "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer $TOKEN"
```

## Common endpoints by module

> Note: Some endpoints require specific roles (admin/executive/planner/etc.).

### Dashboard

```bash
curl -s "http://localhost:8000/api/v1/dashboard/summary" -H "Authorization: Bearer $TOKEN"
curl -s "http://localhost:8000/api/v1/dashboard/alerts"  -H "Authorization: Bearer $TOKEN"
curl -s "http://localhost:8000/api/v1/dashboard/sop-status" -H "Authorization: Bearer $TOKEN"
```

### Products

List products:

```bash
curl -s "http://localhost:8000/api/v1/products?page=1&page_size=20" \
  -H "Authorization: Bearer $TOKEN"
```

Create product (admin):

```bash
curl -s -X POST "http://localhost:8000/api/v1/products" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sku":"SKU-100",
    "name":"Demo Product",
    "status":"active",
    "lead_time_days": 14
  }'
```

Categories:

```bash
curl -s "http://localhost:8000/api/v1/products/categories" \
  -H "Authorization: Bearer $TOKEN"
```

### Demand plans

List:

```bash
curl -s "http://localhost:8000/api/v1/demand/plans?page=1&page_size=20" \
  -H "Authorization: Bearer $TOKEN"
```

Create:

```bash
curl -s -X POST "http://localhost:8000/api/v1/demand/plans" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "period": "2026-03-01",
    "region": "Global",
    "channel": "All",
    "forecast_qty": 1000
  }'
```

Submit:

```bash
curl -s -X POST "http://localhost:8000/api/v1/demand/plans/1/submit" \
  -H "Authorization: Bearer $TOKEN"
```

Approve (executive/admin):

```bash
curl -s -X POST "http://localhost:8000/api/v1/demand/plans/1/approve" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"comment":"Approved"}'
```

### Supply plans

```bash
curl -s "http://localhost:8000/api/v1/supply/plans?page=1&page_size=20" \
  -H "Authorization: Bearer $TOKEN"
```

Gap analysis:

```bash
curl -s "http://localhost:8000/api/v1/supply/gap-analysis?period=2026-03-01" \
  -H "Authorization: Bearer $TOKEN"
```

### Inventory

```bash
curl -s "http://localhost:8000/api/v1/inventory?page=1&page_size=20" \
  -H "Authorization: Bearer $TOKEN"

curl -s "http://localhost:8000/api/v1/inventory/health" \
  -H "Authorization: Bearer $TOKEN"

curl -s "http://localhost:8000/api/v1/inventory/alerts" \
  -H "Authorization: Bearer $TOKEN"
```

### Forecasting

List models:

```bash
curl -s "http://localhost:8000/api/v1/forecasting/models" \
  -H "Authorization: Bearer $TOKEN"
```

Generate:

```bash
curl -s -X POST "http://localhost:8000/api/v1/forecasting/generate?product_id=1&horizon=6" \
  -H "Authorization: Bearer $TOKEN"
```

Generate with specific model:

```bash
curl -s -X POST "http://localhost:8000/api/v1/forecasting/generate?product_id=1&horizon=6&model_type=prophet" \
  -H "Authorization: Bearer $TOKEN"
```

Async generate (enterprise transition pattern):

```bash
curl -s -X POST "http://localhost:8000/api/v1/forecasting/generate-job?product_id=1&horizon=6&model_type=prophet" \
  -H "Authorization: Bearer $TOKEN"
```

Example response shape:

```json
{
  "job_id": "8d2f...",
  "status": "queued",
  "product_id": 1,
  "horizon": 6,
  "model_type": "prophet",
  "requested_by": 1,
  "created_at": "2026-02-27T00:00:00.000000"
}
```

Get async job status/result:

```bash
JOB_ID="<job_id_from_generate_job>"

curl -s "http://localhost:8000/api/v1/forecasting/jobs/$JOB_ID" \
  -H "Authorization: Bearer $TOKEN"
```

List recent jobs:

```bash
curl -s "http://localhost:8000/api/v1/forecasting/jobs?limit=20" \
  -H "Authorization: Bearer $TOKEN"
```

Cancel a job:

```bash
curl -s -X POST "http://localhost:8000/api/v1/forecasting/jobs/$JOB_ID/cancel" \
  -H "Authorization: Bearer $TOKEN"
```

Retry a failed/cancelled job (returns new queued job):

```bash
curl -s -X POST "http://localhost:8000/api/v1/forecasting/jobs/$JOB_ID/retry" \
  -H "Authorization: Bearer $TOKEN"
```

Get job operational metrics:

```bash
curl -s "http://localhost:8000/api/v1/forecasting/jobs/metrics" \
  -H "Authorization: Bearer $TOKEN"
```

Example fields:

- `total_jobs`
- `by_status` (`queued`, `running`, `completed`, `failed`, `cancelled`)
- `avg_processing_time_ms`
- `failed_last_24h`
- `oldest_queued_age_seconds`

Cleanup old jobs (ops roles only):

```bash
curl -s -X POST "http://localhost:8000/api/v1/forecasting/jobs/cleanup?retention_days=30" \
  -H "Authorization: Bearer $TOKEN"
```

If `retention_days` is omitted, backend uses `FORECAST_JOB_RETENTION_DAYS`.

Possible `status` values: `queued`, `running`, `completed`, `failed`, `not_found`.

Results:

```bash
curl -s "http://localhost:8000/api/v1/forecasting/results?product_id=1" \
  -H "Authorization: Bearer $TOKEN"
```

Accuracy:

```bash
curl -s "http://localhost:8000/api/v1/forecasting/accuracy?product_id=1" \
  -H "Authorization: Bearer $TOKEN"
```

Anomalies:

```bash
curl -s -X POST "http://localhost:8000/api/v1/forecasting/anomalies/detect?product_id=1" \
  -H "Authorization: Bearer $TOKEN"
```

### Scenarios

List:

```bash
curl -s "http://localhost:8000/api/v1/scenarios?page=1&page_size=20" \
  -H "Authorization: Bearer $TOKEN"
```

Create:

```bash
curl -s -X POST "http://localhost:8000/api/v1/scenarios" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name":"Upside demand +10%",
    "scenario_type":"what_if",
    "parameters":"{\"demand_pct\": 10}"
  }'
```

Run:

```bash
curl -s -X POST "http://localhost:8000/api/v1/scenarios/1/run" \
  -H "Authorization: Bearer $TOKEN"
```

Compare:

```bash
curl -s -X POST "http://localhost:8000/api/v1/scenarios/compare" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '[1,2,3]'
```

### S&OP cycles

List:

```bash
curl -s "http://localhost:8000/api/v1/sop-cycles?page=1&page_size=20" \
  -H "Authorization: Bearer $TOKEN"
```

Create (admin/coordinator):

```bash
curl -s -X POST "http://localhost:8000/api/v1/sop-cycles" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"cycle_name":"March 2026 S&OP","period":"2026-03-01"}'
```

Advance:

```bash
curl -s -X POST "http://localhost:8000/api/v1/sop-cycles/1/advance" \
  -H "Authorization: Bearer $TOKEN"
```

Complete (admin/executive):

```bash
curl -s -X POST "http://localhost:8000/api/v1/sop-cycles/1/complete" \
  -H "Authorization: Bearer $TOKEN"
```

### KPI

Dashboard:

```bash
curl -s "http://localhost:8000/api/v1/kpi/dashboard" \
  -H "Authorization: Bearer $TOKEN"
```

List metrics:

```bash
curl -s "http://localhost:8000/api/v1/kpi/metrics?category=demand" \
  -H "Authorization: Bearer $TOKEN"
```

## Notes for frontend developers

- The SPA uses Axios interceptors in `frontend/src/services/api.ts` to inject tokens and handle common error codes.
- During local dev, Vite proxies `/api` to the backend (`frontend/vite.config.ts`).
