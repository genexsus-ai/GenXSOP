# Enterprise Inventory Optimization Technical Plan (GenXSOP)

This document defines an enterprise-ready implementation plan to make inventory optimization a core decision layer across **Demand**, **Supply**, and **S&OP** in GenXSOP.

It is designed for phased delivery with governance, security, auditability, scalability, and measurable business outcomes.

---

## 1) Enterprise objectives

### Business objectives

1. Improve service levels while reducing excess inventory and working capital.
2. Convert forecast insight into dynamic policy decisions (not static min/max settings).
3. Enable S&OP executives to make explicit service-cost-cash trade-off decisions.

### Technical objectives

1. Introduce policy outputs per SKU-location-period: safety stock, ROP, target stock, recommended order.
2. Keep full auditability for policy generation, overrides, approvals, and publication.
3. Support enterprise controls (RBAC, exception workflow, KPI governance, performance and observability).

---

## 2) Target capability scope

### Core optimization outputs

- Safety Stock
- Reorder Point (ROP)
- Min/Max or Target Stock
- Recommended Order Quantity and Recommended Date
- Risk flags: stockout risk, excess risk, data-quality risk

### Core optimization inputs

- Demand forecast + error bands (bias/variance/MAPE)
- Lead-time mean/variance by supplier-lane
- Service-level target by segmentation class
- MOQ, lot size, case pack, shelf-life, and capacity constraints
- On-hand, in-transit, allocated, and open order positions

---

## 3) File-by-file implementation blueprint

> Notes:
> - Paths are based on current repository structure.
> - This plan is implementation-ready and can be delivered in phases.

### 3.1 Backend domain model (data layer)

#### A) New/extended models

- **`backend/app/models/inventory.py`**
  - Extend with enterprise policy attributes (if not already present):
    - service_level_target, safety_stock, reorder_point, min_stock, max_stock
    - policy_source (system/manual), policy_version, last_optimized_at
    - risk flags and confidence indicators

- **(Recommended new model) `backend/app/models/inventory_policy_run.py`**
  - Track each optimization execution:
    - run_id, scope filters, input snapshot metadata
    - algorithm_version, status, execution_time
    - user/system actor and timestamps

- **(Recommended new model) `backend/app/models/inventory_policy_exception.py`**
  - Exception management:
    - exception_type (stockout_risk/excess_risk/data_quality)
    - severity, owner, status, due_date, resolution_notes

#### B) Migration files

- **`backend/alembic/versions/`**
  - Add migration(s) for new policy run and exception tables.
  - Add/alter columns in inventory table for optimization fields and audit metadata.
  - Add indexes for SKU-location-period, status, and timestamps.

### 3.2 Backend schemas (API contracts)

- **`backend/app/schemas/inventory.py`**
  - Add request/response schemas:
    - `InventoryPolicyInput`, `InventoryPolicyOutput`, `InventoryPolicyOverride`
    - `InventoryOptimizationRunRequest/Response`
    - `InventoryExceptionView`, `InventoryExceptionUpdate`

- **`backend/app/schemas/kpi.py`**
  - Add enterprise inventory KPI schema fields:
    - fill_rate, inventory_turns, days_of_supply, carrying_cost
    - stockout_rate, expedite_cost, excess_inventory_value

### 3.3 Backend repositories

- **`backend/app/repositories/inventory_repository.py`**
  - Add optimized policy read/write methods by SKU-location-period.
  - Add query filters for risk classes, exceptions, and stale policy detection.

- **(Recommended new) `backend/app/repositories/inventory_policy_run_repository.py`**
  - CRUD + search/pagination for optimization runs.

- **(Recommended new) `backend/app/repositories/inventory_exception_repository.py`**
  - CRUD + assignment/status workflow for exceptions.

### 3.4 Backend services (business logic)

- **`backend/app/services/inventory_service.py`**
  - Add policy computation orchestrator and override workflow.
  - Integrate demand forecast uncertainty and supply constraints.
  - Add audit event emissions for policy changes.

- **`backend/app/services/demand_service.py`**
  - Expose forecast error metrics needed by inventory policy logic.

- **`backend/app/services/supply_service.py`**
  - Expose feasible order constraints (MOQ/lot/capacity/lead-time).

- **`backend/app/services/scenario_service.py`**
  - Add inventory trade-off metrics into scenario calculations.

- **`backend/app/services/kpi_service.py`**
  - Add enterprise inventory KPI computation and trends.

### 3.5 Backend routers (API endpoints)

- **`backend/app/routers/inventory.py`**
  - Add enterprise endpoints:
    - `POST /inventory/optimization/runs`
    - `GET /inventory/optimization/runs/{id}`
    - `GET /inventory/policies`
    - `PUT /inventory/policies/{id}/override`
    - `GET /inventory/exceptions`
    - `PUT /inventory/exceptions/{id}`
  - Enforce role checks for planners/managers/executives.

- **`backend/app/main.py`**
  - Ensure router registration and tags are consistent.

### 3.6 Cross-cutting controls

- **`backend/app/utils/events.py`**
  - Emit policy run and exception lifecycle events for audit traceability.

- **`backend/app/utils/logging.py`**
  - Structured logs with correlation IDs across runs and approvals.

- **`backend/app/core/exceptions.py`**
  - Add domain errors for policy validation, stale data, and unauthorized overrides.

### 3.7 Testing

- **`backend/tests/integration/test_inventory.py`**
  - Add tests for optimization run creation, policy retrieval, override flow, and exception updates.

- **`backend/tests/integration/test_supply.py`**
  - Validate policy-to-supply feasibility interactions.

- **`backend/tests/integration/test_demand.py`**
  - Validate forecast-error inputs consumed by inventory policy.

- **(Recommended new) `backend/tests/integration/test_inventory_optimization.py`**
  - End-to-end scenario: demand update → policy run → exception generation → KPI impact.

---

## 4) Frontend implementation blueprint

### 4.1 Types and contracts

- **`frontend/src/types/index.ts`**
  - Add interfaces for policy, optimization run, exception workflow, and inventory KPI cards.

### 4.2 API services

- **`frontend/src/services/`**
  - Extend/create `inventoryService` methods for new endpoints:
    - run optimization
    - fetch policy list and filters
    - submit overrides
    - manage exceptions
    - fetch inventory KPI trends

### 4.3 UI pages

- **`frontend/src/pages/InventoryPage.tsx`** (if present)
  - Add tabs:
    - Policy Table
    - Exceptions
    - Optimization Runs
    - KPI Trends

- **`frontend/src/pages/SupplyPage.tsx`**
  - Add feasibility signals tied to optimized recommendations.

- **`frontend/src/pages/ScenariosPage.tsx`**
  - Add inventory trade-off charting (service vs cost vs cash).

- **`frontend/src/pages/SOPCyclePage.tsx`**
  - Add inventory policy review gate and signoff summary.

### 4.4 Navigation and permissions

- **`frontend/src/components/layout/Sidebar.tsx`**
  - Add enterprise inventory optimization views if needed.

- **`frontend/src/auth/permissions.ts`**
  - Add permissions for run, override, approve, and publish actions.

---

## 5) Security, compliance, and governance controls

1. **RBAC**
   - Planner: run and propose changes
   - Manager: approve overrides
   - Executive: scenario signoff
   - Admin: policy framework and role administration

2. **Auditability**
   - Capture before/after values for all policy overrides.
   - Store run configuration and algorithm version per optimization run.

3. **Data quality gates**
   - Block publish when critical input quality thresholds fail.
   - Provide override with documented business justification.

4. **Observability**
   - Monitor run duration, failure rates, stale policy age, exception backlog.

---

## 6) Phased delivery plan (enterprise)

### Phase 1 (8–12 weeks): Foundation MVP

- Safety stock + ROP + target stock
- Exception generation (stockout/excess)
- KPI baseline and trend charts
- Approval workflow and audit trail

### Phase 2 (12–20 weeks): Constraint-aware scaling

- Capacity/MOQ/lot-size aware recommendations
- Better scenario comparison metrics
- Enhanced exception triage and ownership dashboards

### Phase 3 (20+ weeks): Network and AI optimization

- Multi-echelon policy optimization
- AI-assisted policy tuning
- Enterprise-wide control tower reporting

---

## 7) KPI and value tracking framework

Track baseline and post-rollout impact by business unit and region:

- Service level / fill rate
- Inventory turns
- Days of supply
- Stockout rate + expedite frequency/cost
- Excess/obsolete inventory value
- Working capital tied in inventory

---

## 8) Definition of done (enterprise-ready)

1. Policy outputs are generated and visible by SKU-location-period.
2. Overrides are role-controlled, approved, and fully auditable.
3. Supply and scenario modules consume inventory optimization outputs.
4. Monthly S&OP includes inventory gate with executive scorecard.
5. KPIs show measurable improvement and are sustained over at least 2 planning cycles.

---

## 9) Recommended next execution step

Implement **Phase 1** in the current codebase with:

1. Backend schema/service/router additions for optimization runs + policy outputs + exceptions.
2. Frontend inventory UI for policy table and exceptions.
3. KPI wiring and integration tests.

This creates the enterprise-ready base for constrained and multi-echelon optimization in later phases.
