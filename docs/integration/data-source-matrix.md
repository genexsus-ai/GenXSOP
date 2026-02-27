# Data Source Matrix (GenXSOP)

This matrix clarifies the **source of truth**, migration approach, and ownership for each major data domain.

## 1) Source-of-data matrix

| Data domain | Primary source of truth | How GenXSOP gets it | Initial migration? | Ongoing sync cadence | Notes |
|---|---|---|---|---|---|
| Users & roles | IAM/HR or manual admin setup | Manual load or API/admin import | Yes | As-needed | Role mapping must align with publish governance |
| Product/SKU master | ERP/MDM | ERP sync endpoint (`/integrations/erp/products/sync`) | Yes | Nightly + on-demand | Includes category and planning attributes |
| Category hierarchy | ERP/MDM | Via product/category mapping during sync | Yes | Nightly | Maintain stable hierarchy keys |
| Locations (plant/warehouse/DC) | ERP/WMS | Inbound sync payloads | Yes | Nightly | Required for inventory/supply context |
| Demand actuals (shipments/sales) | ERP | ERP sync endpoint (`/integrations/erp/demand-actuals/sync`) | Yes (24–36 mo) | Daily | Foundation for forecast training + KPI accuracy |
| Inventory snapshots | WMS/ERP | ERP sync endpoint (`/integrations/erp/inventory/sync`) | Yes (6–12 mo) | Daily (or near real-time) | Capture on-hand, allocated, in-transit |
| Supply execution actuals (optional) | ERP/MES | Batch integration (future/optional) | Optional | Daily/weekly | Useful for service/adherence KPIs |
| Demand plans (approved) | GenXSOP (planning) | Created/approved in-app; optional publish-back | Optional (open plans only) | Continuous | Publish endpoint available after approval gates |
| Supply plans (approved) | GenXSOP (planning) | Created/approved in-app; optional publish-back | Optional (open plans only) | Continuous | Publish endpoint available after approval gates |
| Forecast outputs | GenXSOP ML engine | Generated in GenXSOP | No | As-run | Not migrated from ERP; generated from historical data |
| Scenarios / what-if | GenXSOP | Created in GenXSOP | Optional (active only) | As-needed | Usually migrate only active scenarios |
| S&OP cycle workflow state | GenXSOP | Created/managed in GenXSOP | Optional | Ongoing | Migrate only if continuity is required |
| KPI definitions/targets | BI/Finance or GenXSOP config | Manual seed/import | Yes | Monthly/quarterly review | Separate from KPI measured values |
| Audit logs | GenXSOP (app events) | Auto-generated in app | No (usually) | Continuous | Legacy logs migrate only for compliance need |

## 2) Ownership matrix

| Area | Business owner | Technical owner |
|---|---|---|
| Master data mapping | Demand/Supply leads | Integration/MDM team |
| Demand actual history quality | Demand planning lead | ERP integration team |
| Inventory snapshot quality | Inventory/Supply lead | WMS integration team |
| Publish approvals | S&OP coordinator + executive | App admin/integration team |
| Reconciliation sign-off | PMO + functional leads | Data migration lead |

## 3) Recommended reconciliation checks

- SKU count and active/inactive status parity
- Period-level demand totals by SKU family/region/channel
- Inventory totals by location and SKU family
- Missing key detection (unknown SKUs/locations)
- Duplicate/idempotency checks via `batch_id` + `idempotency_key`

## 4) Related docs

- [`data-migration-scope.md`](data-migration-scope.md)
- [`erp-integration-blueprint.md`](erp-integration-blueprint.md)
- [`erp-wms-integration.md`](erp-wms-integration.md)
- [`publish-readiness.md`](publish-readiness.md)