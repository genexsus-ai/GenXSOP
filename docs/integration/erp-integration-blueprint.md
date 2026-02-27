# ERP/WMS Integration Blueprint (Implementation-Oriented)

This blueprint turns the integration strategy into an actionable technical contract.

## 1) Integration goal

- Keep ERP/WMS as **system of record** for execution transactions.
- Use GenXSOP as **planning + governance system**.
- Start with inbound sync, then controlled publish-back.

## 2) Recommended rollout sequence

### Phase 1 — Master data inbound

Inbound domains:

- Products / SKU master
- Categories / hierarchy
- Locations

Suggested cadence:

- Nightly full sync + on-demand trigger

### Phase 2 — Actuals inbound

Inbound domains:

- Demand actuals (shipments/sales)
- Inventory snapshots
- Optional: supply execution actuals

Suggested cadence:

- Daily batch (or near real-time if available)

### Phase 3 — Publish-back (approved plans only)

Outbound domains:

- Approved demand plans
- Approved supply plans
- Optional inventory policy publish (safety stock/reorder)

Required controls:

- Role-gated publish
- Frozen horizon protection
- Idempotent publish key
- Full audit log

## 3) API contracts (GenXSOP side)

### Inbound endpoints

- `POST /api/v1/integrations/erp/products/sync`
- `POST /api/v1/integrations/erp/inventory/sync`
- `POST /api/v1/integrations/erp/demand-actuals/sync`

All endpoints should support:

- `source_system` (e.g., `SAP_S4`, `Oracle_EBS`)
- `batch_id` and `idempotency_key`
- `dry_run` mode for validation-only runs

### Outbound endpoints

- `POST /api/v1/integrations/erp/publish/demand-plan/{plan_id}`
- `POST /api/v1/integrations/erp/publish/supply-plan/{plan_id}`

Response should include:

- publish status (`accepted`, `rejected`, `already_published`)
- external reference id
- audit correlation id

## 4) Field mapping starter

### Inventory inbound (ERP/WMS -> GenXSOP)

- `material_code` -> `products.sku` lookup
- `site_code` / `warehouse_code` -> `inventory.location`
- `on_hand` -> `inventory.on_hand_qty`
- `allocated` -> `inventory.allocated_qty`
- `in_transit` -> `inventory.in_transit_qty`
- `snapshot_ts` -> `inventory.updated_at`

### Demand actuals inbound

- `material_code` -> `product_id`
- `period` -> `demand_plans.period`
- `actual_qty` -> `demand_plans.actual_qty`

## 5) Ownership model

- IT Integration team: transport, retry, monitoring
- Demand planner lead: demand mapping validation
- Supply/inventory lead: inventory and supply mapping validation
- S&OP coordinator: publish governance and approvals

## 6) Production readiness checklist

- [ ] Contract tests for each payload
- [ ] Idempotency + replay safety verified
- [ ] Dead-letter queue/retry policy defined
- [ ] Monitoring dashboards and alerts in place
- [ ] Runbook for sync failure and publish rollback
