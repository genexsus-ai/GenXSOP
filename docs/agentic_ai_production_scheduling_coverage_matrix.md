# Agentic AI Production Scheduling — Requirements Coverage Matrix

Source of truth: `agentic_ai_production_scheduling_requirements.md`

Legend:
- ✅ Implemented
- 🟡 Partial
- ❌ Missing

## 1) Overview / Scope

| Requirement Area | Status | Evidence in Codebase | Notes |
|---|---|---|---|
| Event-driven adaptive production scheduling | ✅ | `backend/app/routers/production_scheduling.py`, `backend/app/services/agentic_scheduling_service.py` | Real-time recommendation endpoint + workflow state handling present |
| Human-in-the-loop recommendation lifecycle | ✅ | Approve/reject/modify/publish endpoints + transition guards in `agentic_scheduling_service.py` | Guardrails tested in integration suite |
| Single-app integrated architecture (React + FastAPI) | ✅ | `frontend/` + `backend/` monorepo, layered backend modules | Modular monolith pattern aligned with container guidance |

## 2) Functional Requirements

### 2.1 Data Integration

| Requirement | Status | Evidence | Notes |
|---|---|---|---|
| ERP/MES/IIoT/QMS/CMMS event handling | 🟡 | Canonical ingest + normalization in `backend/app/services/integration_service.py` | Adapters are normalized in-service; not fully separated adapter modules |
| Streaming & batch ingestion | 🟡 | Event ingest + existing sync endpoints | Streaming path exists (SSE out); event broker-native streaming and full batch pipelines are partial |
| Schema validation | ✅ | Pydantic schemas in `backend/app/schemas/integration.py`, `agentic_scheduling.py` | Enforced at API boundary |
| Timestamp alignment / out-of-order handling | ✅ | Out-of-order policy + retry/dead-letter context in `integration_service.py` | Covered by `test_canonical_event_out_of_order_and_retry_budget_dead_letter_context` |
| Data lineage tracking | 🟡 | `correlation_id`, `trace_id`, audit/event metadata | End-to-end lineage/reporting UI not fully complete |

### 2.2 Scheduling Engine

| Requirement | Status | Evidence | Notes |
|---|---|---|---|
| Finite capacity scheduling | 🟡 | `production_schedule_service.py` generation/capacity summary | Basic slot/capacity logic exists; advanced solver depth limited |
| Alternate routings | ❌ | N/A | Not explicitly implemented |
| Machine eligibility rules | 🟡 | Workcenter/line scoping and filtering | No formal eligibility rule engine/catalog |
| Labor constraints | 🟡 | Shift-level scheduling fields | Skill/availability optimization limited |
| Material availability integration | 🟡 | Event signals (`MATERIAL_SHORTAGE`) and recommendations | Not full MRP-grade constrained optimizer |
| Sequence-dependent setup optimization | 🟡 | Resequence and orchestration scoring includes changeover penalty | No full setup-matrix optimizer yet |
| Schedule version comparison | ✅ | Snapshot + compare endpoints in `production_scheduling.py` and service | Tested |

### 2.3 Event-driven Scheduling Triggers

| Trigger | Status | Evidence |
|---|---|---|
| MACHINE_DOWN / MACHINE_RECOVERED | ✅ | Supported event types + tests |
| ORDER_PRIORITY_CHANGED | ✅ | Supported event types + tests |
| MATERIAL_SHORTAGE | ✅ | Supported event types + recommendation logic |
| QUALITY_HOLD / QUALITY_RELEASED | ✅ | Supported event types + recommendation logic |
| LABOR_UNAVAILABLE | ✅ | Supported event types + recommendation logic |
| DOWNTIME_PLANNED / WIP_UPDATED / ORDER_RELEASED | ✅ | Added in P1 continuation + tests |

### 2.4 Human in the Loop

| Requirement | Status | Evidence | Notes |
|---|---|---|---|
| Approve/reject recommendations | ✅ | `/recommendations/{id}/approve|reject` | Transition guards enforced |
| Modify sequence / recommendation | ✅ | `/recommendations/{id}/modify` + resequence endpoint | |
| Run simulations / compare alternatives | 🟡 | P2 orchestration alternative scoring + simulated KPI deltas | Dedicated simulation API/workbench parity still partial |
| Decision audit trail | ✅ | Recommendation decision metadata + snapshots + event/audit patterns | Dedicated consolidated audit UI still partial |

## 3) Agent Architecture (Planner/Constraint/Optimization/Simulation/Exception/Explanation/Integration)

| Agent Role | Status | Evidence | Notes |
|---|---|---|---|
| Exception classification | ✅ | Event-type classification in `agentic_scheduling_service.py` | Rule/heuristic-based |
| Planner action proposal | ✅ | `_build_actions(...)` | Heuristic planner agent |
| Constraint validation | ✅ | `_constraint_pass(...)` in `agentic_orchestration_service.py` | Basic constraint gate |
| Optimization ranking | ✅ | Weighted scoring in orchestration service | Objective weights exposed in P2 |
| Simulation impact | ✅ | `simulated_kpis` and risk indicators in orchestration alternatives | Expanded in P2 |
| Explanation generation | 🟡 | Recommendation summary/explanation text | No dedicated LLM explanation agent pipeline |
| Integration agent | 🟡 | Event normalization + connectors in `integration_service.py` | Not yet a separate pluggable adapter framework |

## 4) API Spec Coverage (selected)

| API Group in Requirements | Status | Evidence |
|---|---|---|
| Scheduling endpoints | ✅ | generate/list/resequence/status + versions/compare |
| Recommendations endpoints | ✅ | list/get/approve/reject/modify/publish |
| Events endpoints | ✅ | ingest/list/replay + event recommendation |
| Simulation endpoints | 🟡 | Simulated KPI output exists; dedicated simulation resource set partial |
| Audit endpoints | 🟡 | Audit data captured; explicit `/api/v1/audit/*` surface incomplete |
| Config objectives/policies endpoints | ❌ | Not fully implemented as dedicated config APIs |

## 5) Non-functional Requirements

| Requirement | Status | Evidence | Notes |
|---|---|---|---|
| Reliability (retry/dead-letter/replay) | ✅ | Production event reliability hardening + replay endpoint/tests | |
| Observability (structured events/logging) | 🟡 | Logging + EventBus patterns + request middleware in repo | Full metrics/tracing/SLO stack partial |
| Security (RBAC/auth) | ✅ | JWT + role guards in router dependencies | |
| Immutable audit trail | 🟡 | Audit/event records present | Full immutability/compliance controls partial |

## 6) Frontend Coverage

| UI Capability | Status | Evidence | Notes |
|---|---|---|---|
| Production scheduling page | ✅ | `frontend/src/pages/ProductionSchedulingPage.tsx` | |
| Production control tower page | ✅ | `frontend/src/pages/ProductionControlTowerPage.tsx` | Recommendation + version compare views present |
| Recommendation review panel behavior | ✅ | Approve/reject/modify/publish flows wired via frontend service/types | |
| Dedicated simulation workspace depth | 🟡 | Version compare and KPI views | Full what-if simulation workflow still growing |
| Audit viewer depth | 🟡 | Recommendation audit section exists | Broader cross-domain audit views partial |

## 7) Overall Conclusion

Current implementation is **substantial but not complete** relative to the full requirement document.

- **Strongly implemented**: event ingestion reliability, event-driven recommendation lifecycle, approval/publish guardrails, schedule versioning/compare, and P2 orchestration simulation enrichments.
- **Partially implemented**: deeper constraint solver capabilities, formalized multi-agent runtime decomposition, full simulation/audit/config API parity, and enterprise-grade observability/compliance envelope.
- **Missing**: some roadmap-level capabilities (e.g., full objective/policy config APIs, complete alternate-routing/eligibility rule engine).

## 8) Recommended Next Slice (P2 -> P3 Bridge)

1. Add dedicated **Objectives/Policies Config APIs** (`/api/v1/config/objectives`, `/api/v1/config/policies`) and persistence.
2. Introduce a **constraint catalog** abstraction (machine eligibility, labor skill, setup matrix) with explicit validation chain.
3. Add a first-class **Simulation API resource** (`POST /simulations`, `GET /simulations/{id}`) backed by persisted runs.
4. Expand UI to display **objective weights, risk indicators, and simulation alternatives** explicitly in control tower/recommendation panels.
