# Data Migration Scope for GenXSOP

This document defines **what data should be migrated** into GenXSOP and which data should remain in source enterprise systems.

## 1) Migration objective

- Load enough historical and master data for planning, forecasting, S&OP workflow, and KPI reporting.
- Keep ERP/WMS as system of record for execution transactions.
- Avoid migrating unnecessary operational history that does not support planning decisions.

## 2) Scope summary

### In scope for migration / onboarding

1. **Master data**
   - Products/SKUs
   - Category hierarchy
   - Locations/plants/warehouses
   - Lead times and key planning attributes

2. **Planning baseline history**
   - Demand actuals (sales/shipments)
   - Inventory snapshots (on-hand, allocated, in-transit)
   - Optional supply execution actuals (receipts/production) if needed for KPI depth

3. **Planning configuration & governance**
   - User accounts and roles
   - S&OP cycle setup
   - KPI definitions and targets

4. **Open planning records (optional cutover choice)**
   - Current open demand plans
   - Current open supply plans
   - Active scenarios (if business wants continuity)

### Out of scope (remain in ERP/WMS)

- Full transactional order line history (unless specifically required)
- Procurement/work-order execution details at full granularity
- Financial posting-level ledger details
- Legacy workflow comments/logs that are not needed for compliance

## 3) Recommended historical depth

- **Demand actuals:** 24–36 months (minimum 12)
- **Inventory snapshots:** 6–12 months (minimum 3)
- **Master data:** current active set + optionally recently inactive SKUs used in recent history
- **Open plans/scenarios:** latest approved + in-flight versions only

## 4) Migration waves

### Wave 1 — Foundation

- Users/roles
- Categories/products
- Locations

### Wave 2 — Historical baseline

- Demand actuals history
- Inventory history

### Wave 3 — Planning continuity

- Open demand/supply plans (if applicable)
- KPI targets and initial dashboards
- Active scenarios and S&OP cycle state (if applicable)

### Wave 4 — Integration steady state

- Switch from one-time migration to regular ERP/WMS sync jobs
- Enable publish-back for approved plans when governance gates are met

## 5) Cutover decision points

Before go-live, decide:

1. Whether open plans are migrated vs re-created in GenXSOP
2. Which system is authoritative for each domain during transition
3. Freeze window for final legacy extracts
4. Reconciliation thresholds (e.g., inventory and demand totals by period/location)

## 6) Acceptance criteria

- Product/SKU mapping completeness ≥ 99%
- No orphan demand/inventory records (all SKUs resolve)
- Period totals reconciled with source systems within agreed tolerance
- User roles validated for publish governance
- Auditability confirmed for migration loads (batch_id/idempotency)

## 7) Related docs

- [`erp-wms-integration.md`](erp-wms-integration.md)
- [`erp-integration-blueprint.md`](erp-integration-blueprint.md)
- [`publish-readiness.md`](publish-readiness.md)
- [`data-source-matrix.md`](data-source-matrix.md)