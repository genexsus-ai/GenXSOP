# GenXSOP Enterprise Readiness Plan (Reference + Execution)

This document defines a practical path to move GenXSOP from strong product architecture to enterprise-grade operational maturity.

## 1) Objective

Deliver enterprise-level outcomes across:

- Security & Identity
- Reliability & Scalability
- Observability & Operations
- Governance, Compliance, and Integration Control

## 2) Current baseline (from existing architecture)

GenXSOP already has:

- Layered backend architecture (routers/services/repositories)
- JWT auth and role-based authorization controls
- Domain exception hierarchy and consistent API error model
- EventBus-based audit/event logging pattern
- Integration and unit test suites
- Deployment guidance for reverse proxy + API + database

## 3) Gap areas to close for enterprise readiness

1. Enterprise SSO and identity lifecycle (OIDC/SAML + provisioning)
2. Asynchronous compute for heavy forecasting workloads
3. Full observability stack (metrics, tracing, SLO-driven operations)
4. Stronger data constraints and migration discipline
5. Security pipeline gates and vulnerability response SLAs
6. Publish/readiness governance fully enforced in code
7. HA/DR drills and documented incident runbooks

## 4) Phased roadmap

### Phase 1 (0–90 days): Foundation hardening

- Implement request correlation IDs and security headers in API responses
- Add readiness-style health endpoint for operational checks
- Establish CI security gates (SAST, dependency scanning)
- Start enterprise auth design (OIDC/SAML integration plan)
- Define SLO/SLI baseline and alerting thresholds

### Phase 2 (90–180 days): Scale + governance

- Introduce async job queue for forecasting and anomaly detection
- Add cache strategy for dashboard and read-heavy APIs
- Enforce publish Go/No-Go gates in service workflows
- Strengthen DB constraints/indexes via Alembic migrations

### Phase 3 (180+ days): Certification + enterprise operations

- Formal compliance controls (SOC2-oriented evidence model)
- DR drills with RPO/RTO evidence
- Enterprise support model (on-call, runbooks, SLAs)

## 5) KPI targets

- Availability: >= 99.9%
- Non-ML API latency (p95): < 300ms
- Forecast job success rate: >= 99.5%
- Critical vulnerabilities: 0 open beyond SLA
- Publish actions with enforced gate validation: 100%

## 6) Immediate implementation in this repository

This plan is not only theoretical. The initial foundation hardening implemented now includes:

1. Request ID middleware for correlation across logs and responses
2. Security response headers middleware
3. Dedicated readiness endpoint (`/ready`) with request ID support
4. Config flags to control these behaviors by environment
5. Async forecasting job endpoints (`/forecasting/generate-job`, `/forecasting/jobs/{job_id}`)
6. Production safety guardrails for database configuration (`ENVIRONMENT`, `AUTO_CREATE_TABLES`, production checks)
7. Stronger enterprise data constraints and indexes for core planning tables (via Alembic)

### Async forecasting note

Current implementation uses an in-process worker (`ThreadPoolExecutor`) as a transition step.
For full enterprise durability and scale, move this interface to external queue workers
(Celery/RQ + Redis/RabbitMQ) with persistent job state.

Current state in repository:

- Job metadata/status is persisted in `forecast_jobs` database table.
- Result payload is stored as JSON text (`result_json`) and returned through job status API.
- Operational job metrics endpoint is available at `/forecasting/jobs/metrics`.
- Operational controls (`/jobs`, `/jobs/{id}/cancel`, `/jobs/{id}/retry`, `/jobs/metrics`) are restricted to ops roles (`admin`, `sop_coordinator`, `executive`).
- Retention cleanup endpoint available: `/forecasting/jobs/cleanup` (ops roles), controlled by `FORECAST_JOB_RETENTION_DAYS`.
- Lightweight maintenance runner added: `backend/app/services/forecast_job_maintenance.py` (`run_forecast_job_cleanup`) for cron/scheduler integration.
- Initial migration file added: `backend/alembic/versions/20260227_0001_add_forecast_jobs_table.py`.
- Enterprise hardening migration added: `backend/alembic/versions/20260227_0002_enterprise_db_hardening.py`.
  - Adds composite business-key uniqueness constraints
  - Adds status-domain and non-negative/range check constraints
  - Adds operational composite indexes for common filter patterns
- Data quality normalization migration added: `backend/alembic/versions/20260227_0003_data_quality_backfill.py`.
  - Backfills legacy/invalid values (status domains, empty dimensions, negative values)
  - Reduces risk of enterprise constraint conflicts during upgrades

### Operational reference for implemented controls

#### Environment flags

- `ENABLE_REQUEST_ID` (default: `true`)
- `ENABLE_REQUEST_LOGGING` (default: `true`)
- `ENABLE_SECURITY_HEADERS` (default: `true`)
- `STRICT_TRANSPORT_SECURITY_SECONDS` (default: `31536000`)
- `READINESS_CHECK_DATABASE` (default: `true`)
- `LOG_LEVEL` (default: `INFO`)
- `LOG_FORMAT` (default: `json`, supported: `json`, `standard`)

#### Verification commands

```bash
curl -i http://localhost:8000/health
curl -i -H 'X-Request-ID: enterprise-check-001' http://localhost:8000/health
curl -i http://localhost:8000/ready
```

Expected outcomes:

- Responses include `X-Request-ID` and `X-Response-Time-Ms`
- Security headers are present when enabled
- `/ready` returns database check status and `200` when DB is reachable
- Request-completion logs are emitted in structured JSON when `LOG_FORMAT=json`

## 7) Backlog epics for tracking

- EPIC-1 Identity & Access Enterpriseization
- EPIC-2 Forecasting Compute Scalability
- EPIC-3 Observability & SRE Foundations
- EPIC-4 Data Governance & Integrity
- EPIC-5 Secure SDLC & Compliance Readiness
- EPIC-6 Integration Reliability (ERP/WMS/BI)

## 8) Definition of “Enterprise Ready” for GenXSOP

GenXSOP is considered enterprise ready when all are true:

- Technical controls are implemented and measurable (not just documented)
- Operational targets are monitored and consistently achieved
- Security/compliance evidence is auditable and repeatable
- Business publish workflows are policy-gated and reversible
