# GenXSOP User Guide

This guide explains how to use the main features of the GenXSOP web application.

## Screenshots

If you want to turn this into a “product manual”, you can add screenshots under:

- `docs/assets/user-guide/`

Suggested filenames are listed in each section below.

> Tip: You can always see the full API surface in Swagger at `http://localhost:8000/docs`.

## 1) Login / Logout

**Screenshot (suggested):** `docs/assets/user-guide/login.png`

### Login

1. Open the frontend: `http://localhost:5173`
2. Navigate to **Login**.
3. Enter your email + password.
4. Click **Sign In**.

What happens:

- The app calls `POST /api/v1/auth/login`.
- A JWT access token is stored locally and used for subsequent requests.

### Logout

- Use the user menu (top-right) and click **Logout**.

## 2) Dashboard

**Screenshot (suggested):** `docs/assets/user-guide/dashboard.png`

Navigate: **Sidebar → Dashboard**

Use the dashboard to:

- View summary KPIs
- View alerts
- Track S&OP cycle status

Behind the scenes (API):

- `GET /api/v1/dashboard/summary`
- `GET /api/v1/dashboard/alerts`
- `GET /api/v1/dashboard/sop-status`

## 3) Products & Categories (Master Data)

**Screenshot (suggested):** `docs/assets/user-guide/products.png`

Navigate: **Sidebar → Products**

### Categories

- List categories: the UI loads `GET /api/v1/products/categories`.
- Create category (admin only): UI posts to `POST /api/v1/products/categories`.

### Products

Typical flow:

1. Add a product SKU, name, optional category.
2. Keep product status as `active`.
3. Use search/filter to find products.

Notes:

- Creating/updating products requires the **admin** role.
- “Delete” is a *soft delete* (sets status to `discontinued`).

Behind the scenes (API):

- `GET /api/v1/products?page=1&page_size=20&status=active&search=...`
- `POST /api/v1/products`
- `PUT /api/v1/products/{product_id}`
- `DELETE /api/v1/products/{product_id}`

## 4) Demand Planning

**Screenshot (suggested):** `docs/assets/user-guide/demand.png`

Navigate: **Sidebar → Demand**

Use this module to manage the demand plan by product/period/region/channel.

### View demand plans

1. Open Demand.
2. Filter by product/period range/region/channel/status.
3. Review plan quantities and statuses.

API:

- `GET /api/v1/demand/plans?page=1&page_size=20&product_id=...&period_from=YYYY-MM-DD&period_to=YYYY-MM-DD`

### Create a demand plan

1. Click **New Plan**.
2. Choose product + period.
3. Enter `forecast_qty`.
4. Save.

API:

- `POST /api/v1/demand/plans`

Requires role: `admin`, `demand_planner`, `supply_planner`, or `sop_coordinator`.

### Adjust a forecast (planner adjustment)

1. Open a plan.
2. Click **Adjust**.
3. Enter the adjustment value (per the UI).
4. Save.

API:

- `POST /api/v1/demand/plans/{plan_id}/adjust`

### Submit / Approve / Reject

Workflow:

1. Planner **submits** a plan.
2. Executive/Admin **approves** or **rejects** with an optional comment.

API:

- `POST /api/v1/demand/plans/{plan_id}/submit`
- `POST /api/v1/demand/plans/{plan_id}/approve`
- `POST /api/v1/demand/plans/{plan_id}/reject`

## 5) Supply Planning

**Screenshot (suggested):** `docs/assets/user-guide/supply.png`

Navigate: **Sidebar → Supply**

### View supply plans

- `GET /api/v1/supply/plans?...`

### Create / update supply plans

- `POST /api/v1/supply/plans`
- `PUT /api/v1/supply/plans/{plan_id}`

### Submit / Approve

- `POST /api/v1/supply/plans/{plan_id}/submit`
- `POST /api/v1/supply/plans/{plan_id}/approve`

### Gap analysis

Use **Gap analysis** to compare supply vs demand for a given period.

- `GET /api/v1/supply/gap-analysis?period=YYYY-MM-DD`

## 6) Inventory Management

**Screenshot (suggested):** `docs/assets/user-guide/inventory.png`

Navigate: **Sidebar → Inventory**

### View inventory list

- `GET /api/v1/inventory?page=1&page_size=20&status=...`

### Inventory health summary

- `GET /api/v1/inventory/health`

### Inventory alerts

- `GET /api/v1/inventory/alerts`

### Update an inventory record

Requires role: `admin`, `inventory_manager`, or `supply_planner`.

- `PUT /api/v1/inventory/{inventory_id}`

## 7) Forecasting (AI/ML)

**Screenshot (suggested):** `docs/assets/user-guide/forecasting.png`

Navigate: **Sidebar → Forecasting**

### List available models

- `GET /api/v1/forecasting/models`

Current models include:

- Moving Average
- EWMA
- Exponential Smoothing
- Seasonal Naive
- ARIMA
- Prophet

### Generate a forecast

1. Pick a product.
2. Choose horizon (months).
3. Optionally choose a model (or leave blank for auto-select).
4. Click **Generate**.

API:

- `POST /api/v1/forecasting/generate?product_id=1&horizon=6&model_type=prophet`

### Promote forecast result to Demand Plan

Use **Manage Forecast Results** to select a model per product and promote it into Demand Planning.

1. Go to **Forecasting → Manage Results**.
2. Locate the product + model row.
3. Click **Promote**.
4. Confirm action.

API:

- `POST /api/v1/forecasting/promote?product_id=1&selected_model=arima&horizon=6`

What promotion does:

- Applies selected model output into demand plans for the forecast periods.
- Preserves planner control (human-in-the-loop decision).
- Stores promotion context in plan notes/version history.

### View results

- `GET /api/v1/forecasting/results?product_id=1&model_type=prophet`

### Accuracy metrics

- `GET /api/v1/forecasting/accuracy?product_id=1`

### Detect anomalies

- `POST /api/v1/forecasting/anomalies/detect?product_id=1`

## 8) Scenarios (What-if)

**Screenshot (suggested):** `docs/assets/user-guide/scenarios.png`

Navigate: **Sidebar → Scenarios**

### Create and run

1. Create a scenario with parameter changes.
2. Click **Run** to compute results.
3. Submit for approval if needed.

API:

- `POST /api/v1/scenarios`
- `POST /api/v1/scenarios/{scenario_id}/run`
- `POST /api/v1/scenarios/{scenario_id}/submit`

### Approve / reject

- `POST /api/v1/scenarios/{scenario_id}/approve`
- `POST /api/v1/scenarios/{scenario_id}/reject`

### Compare

- `POST /api/v1/scenarios/compare` (with a list of IDs)

## 9) S&OP Cycle

**Screenshot (suggested):** `docs/assets/user-guide/sop-cycle.png`

Navigate: **Sidebar → S&OP Cycle**

### Create a cycle

Requires role: `admin` or `sop_coordinator`.

- `POST /api/v1/sop-cycles`

### Advance step

- `POST /api/v1/sop-cycles/{cycle_id}/advance`

### Complete cycle

Requires role: `admin` or `executive`.

- `POST /api/v1/sop-cycles/{cycle_id}/complete`

### Check active cycle

- `GET /api/v1/sop-cycles/active`

## 10) KPI Dashboard

**Screenshot (suggested):** `docs/assets/user-guide/kpi.png`

Navigate: **Sidebar → KPI**

### View KPI dashboard

- `GET /api/v1/kpi/dashboard`

### List KPI metrics

- `GET /api/v1/kpi/metrics?category=inventory&period_from=YYYY-MM-DD&period_to=YYYY-MM-DD`

### Create KPI metric / set targets

Requires role: `admin` or `executive`.

- `POST /api/v1/kpi/metrics`
- `POST /api/v1/kpi/targets`

## 11) Settings

**Screenshot (suggested):** `docs/assets/user-guide/settings.png`

Navigate: **Sidebar → Settings**

Typically used for UI preferences and future administrative settings.
