# Epicor Kinetic → GenXSOP Integration Guide

This document consolidates the recommended approach for moving data between **Epicor Kinetic ERP** and **GenXSOP**.

---

## 1) Do we need API to move data?

Short answer: **API is recommended**, but not the only option.

Options:

1. **API integration (recommended default)**
   - Best for reliability, security, maintainability, and near real-time sync.
2. **File-based batch (CSV/XML via SFTP/shared storage)**
   - Good for nightly/batch integrations.
3. **Direct database access (last resort, typically read-only)**
   - Usually discouraged due to upgrade risk and bypassing application logic.

For Kinetic + GenXSOP, use **API + BAQ-driven extracts** as the preferred pattern.

---

## 2) GenXSOP APIs available for ERP integration

Base prefix: `/api/v1/integrations`

Inbound (ERP → GenXSOP):

- `POST /erp/products/sync`
- `POST /erp/inventory/sync`
- `POST /erp/demand-actuals/sync`

Outbound publish (GenXSOP → ERP):

- `POST /erp/publish/demand-plan/{plan_id}`
- `POST /erp/publish/supply-plan/{plan_id}`

Notes:

- Require authentication and integration roles (`admin` or `sop_coordinator`).
- Integration payload contracts are defined in `backend/app/schemas/integration.py`.

---

## 3) Inbound payload contract (shared envelope)

All inbound endpoints use:

```json
{
  "meta": {
    "source_system": "EpicorKinetic",
    "batch_id": "KIN-XXX-20260227-001",
    "idempotency_key": "kin-xxx-001",
    "dry_run": false
  },
  "items": []
}
```

`meta` fields:

- `source_system` (required): e.g. `EpicorKinetic`
- `batch_id` (optional but strongly recommended): unique per execution
- `idempotency_key` (optional but strongly recommended): replay safety / dedupe
- `dry_run` (optional, default `false`): validation-only mode

---

## 4) Ready-to-use curl examples

```bash
TOKEN="<your_access_token>"
BASE="http://localhost:8000/api/v1"
```

### 4.1 Products sync

```bash
curl -X POST "$BASE/integrations/erp/products/sync" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "meta": {
      "source_system": "EpicorKinetic",
      "batch_id": "KIN-PROD-20260227-001",
      "idempotency_key": "kin-prod-001",
      "dry_run": false
    },
    "items": [
      {
        "sku": "FG-1001",
        "name": "Widget A",
        "category_name": "Finished Goods",
        "product_family": "Widgets",
        "lead_time_days": 14
      }
    ]
  }'
```

### 4.2 Inventory sync

```bash
curl -X POST "$BASE/integrations/erp/inventory/sync" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "meta": {
      "source_system": "EpicorKinetic",
      "batch_id": "KIN-INV-20260227-001",
      "idempotency_key": "kin-inv-001",
      "dry_run": false
    },
    "items": [
      {
        "sku": "FG-1001",
        "location": "MAIN-WH",
        "on_hand_qty": 1250,
        "allocated_qty": 200,
        "in_transit_qty": 75
      }
    ]
  }'
```

### 4.3 Demand actuals sync

```bash
curl -X POST "$BASE/integrations/erp/demand-actuals/sync" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "meta": {
      "source_system": "EpicorKinetic",
      "batch_id": "KIN-DA-20260227-001",
      "idempotency_key": "kin-da-001",
      "dry_run": false
    },
    "items": [
      {
        "sku": "FG-1001",
        "period": "2026-02-01",
        "actual_qty": 980,
        "region": "NA",
        "channel": "Direct"
      }
    ]
  }'
```

### 4.4 Publish plans back to ERP

```bash
# Publish demand plan
curl -X POST "$BASE/integrations/erp/publish/demand-plan/123" \
  -H "Authorization: Bearer $TOKEN"

# Publish supply plan
curl -X POST "$BASE/integrations/erp/publish/supply-plan/456" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 5) Kinetic BAQ → GenXSOP field mapping template

Use this starter mapping when shaping BAQ outputs.

### 5.1 Products (`/erp/products/sync`)

- `Part.PartNum` → `items[].sku`
- `Part.PartDescription` → `items[].name`
- `Part.ProdCode` (or custom category field) → `items[].category_name`
- `Part.ClassID` / product family field → `items[].product_family`
- `Part.LeadTime` (or planning lead time) → `items[].lead_time_days`

### 5.2 Inventory (`/erp/inventory/sync`)

- `PartBin.PartNum` → `items[].sku`
- `PartBin.WarehouseCode` + `PartBin.BinNum` (or warehouse only) → `items[].location`
- `PartBin.OnhandQty` → `items[].on_hand_qty`
- `PartAlloc.AllocatedQty` (if available) → `items[].allocated_qty`
- Open transfer quantity / in-transit calc → `items[].in_transit_qty`

### 5.3 Demand actuals (`/erp/demand-actuals/sync`)

- `OrderDtl.PartNum` (or invoice line part) → `items[].sku`
- Month bucket from `InvoiceDtl.InvoiceDate` (or ship date) → `items[].period` (`YYYY-MM-01`)
- Sum shipped/invoiced quantity by period → `items[].actual_qty`
- `Customer.Region` / territory mapping → `items[].region`
- `OrderHed.Channel` (or derived mapping) → `items[].channel`

---

## 6) Sample BAQ output schema (recommended)

### BAQ: `GenXSOP_Product_Master`

- `sku` (string, required)
- `name` (string, required)
- `category_name` (string, nullable)
- `product_family` (string, nullable)
- `lead_time_days` (int, nullable)

### BAQ: `GenXSOP_Inventory_Snapshot`

- `sku` (string, required)
- `location` (string, required)
- `on_hand_qty` (decimal, required)
- `allocated_qty` (decimal, default 0)
- `in_transit_qty` (decimal, default 0)

### BAQ: `GenXSOP_Demand_Actuals_Monthly`

- `sku` (string, required)
- `period` (date, required, first day of month)
- `actual_qty` (decimal, required)
- `region` (string, default `Global`)
- `channel` (string, default `All`)

---

## 7) Recommended go-live sequence

1. Build and validate BAQs with exact contract columns.
2. Load each endpoint with `dry_run=true`.
3. Resolve unknown SKUs/locations and date/period formatting issues.
4. Re-run using same `idempotency_key` to verify no duplicates.
5. Execute production load (`dry_run=false`).
6. Reconcile totals/counts between Kinetic and GenXSOP.
7. Schedule operations:
   - Products: nightly + on-demand
   - Inventory: daily (or more frequent)
   - Demand actuals: daily

---

## 8) Production readiness checklist

- [ ] Contract tests for all three inbound payloads
- [ ] Idempotency/replay behavior validated
- [ ] Retry and dead-letter handling defined
- [ ] Monitoring + alerting configured
- [ ] Operational runbook (sync failure + rollback) approved
- [ ] Business reconciliation sign-off completed

---

## 9) Related references

- `docs/api-guide.md`
- `docs/integration/erp-integration-blueprint.md`
- `docs/integration/data-source-matrix.md`
- `docs/integration/data-migration-scope.md`
- `docs/integration/publish-readiness.md`
