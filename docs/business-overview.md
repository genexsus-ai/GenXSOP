# GenXSOP Business Overview

GenXSOP is a **Sales & Operations Planning (S&OP)** platform that helps an organization align **demand**, **supply**, **inventory**, and **financial outcomes** using a single workflow-driven application.

It is designed to replace fragmented spreadsheet-based planning with:

- **One source of truth** for plans and KPIs
- **Role-based workflow and approvals**
- **AI/statistical forecasting** and anomaly detection
- **Scenario planning** (what-if analysis)
- **S&OP cycle governance** (5-step process)

## What problem it solves

Typical pain points GenXSOP addresses:

- Planning data scattered across spreadsheets and teams
- Conflicting versions of demand/supply/inventory plans
- Slow, manual monthly cycles with weak accountability
- Limited decision support (hard to quantify tradeoffs)
- Poor visibility into exceptions (stockouts, constraints, KPI breaches)

## Who uses it

GenXSOP supports these roles (with role-based access control):

- **Executive / Leadership**: reviews KPIs, approves plans and scenarios, makes final decisions
- **S&OP Coordinator**: manages the cycle steps, assigns owners, advances the workflow
- **Demand Planner**: creates/adjusts demand plans, runs forecasts, submits for approval
- **Supply Planner**: creates supply plans, manages capacity/constraints, runs gap analysis
- **Inventory Manager**: manages inventory health, safety stock/reorder points, alerts
- **Finance Analyst**: runs scenarios and evaluates financial impacts
- **Admin**: manages users and master data (products/categories)

## What’s in the platform (modules)

From the left sidebar in the UI:

- **Dashboard**: executive overview (summary KPIs, alerts, S&OP status)
- **Products**: product and category master data
- **Demand**: demand planning (create, adjust, submit, approve)
- **Supply**: supply planning (capacity, constraints, submit/approve, gap analysis)
- **Inventory**: inventory health, alerts, parameter tuning
- **Forecasting**: forecasting models, generation, accuracy metrics, anomalies
- **Scenarios**: what-if simulations and comparisons
- **S&OP Cycle**: the 5-step workflow governance
- **KPI**: KPI dashboards, trends, alerts/targets
- **Settings**: UI preferences and future admin settings

## The “month-in-the-life” S&OP workflow

This is a common end-to-end usage pattern:

1. **Admin** maintains products/categories and user access.
2. **Demand Planner** generates statistical forecasts and adjusts demand plans.
3. **Demand plan** is **submitted** and then **approved/rejected**.
4. **Supply Planner** builds a supply plan and runs **gap analysis** vs demand.
5. **Supply plan** is **submitted** and then **approved/rejected**.
6. **Inventory Manager** reviews inventory health/alerts and updates policy parameters.
7. **Finance Analyst** runs scenarios to quantify tradeoffs and impacts.
8. **S&OP Coordinator** advances the monthly cycle steps and ensures gates are met.
9. **Executives** review KPIs, approve the final plan/scenario, and make decisions.

## Start here

- UI walkthrough: [`user-guide.md`](user-guide.md)
- Developer/API guide: [`api-guide.md`](api-guide.md)
- Architecture docs: [`architecture/README.md`](architecture/README.md)
