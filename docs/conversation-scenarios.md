# Conversation Scenarios (End-to-End Narrative)

This document captures the scenarios discussed in the conversation that led to these docs.

## 1) “What is this app for?” (high-level)

GenXSOP is a full-stack **Sales & Operations Planning (S&OP) platform** that aligns demand, supply, inventory, and financial KPIs with workflow and approvals.

## 2) Business user perspective

The app is used as a monthly/weekly workspace to:

- Review KPIs and alerts (Dashboard/KPI)
- Build demand plans (Demand)
- Build supply plans and gap analysis (Supply)
- Monitor inventory health (Inventory)
- Generate forecasts and measure accuracy (Forecasting)
- Run what-if simulations (Scenarios)
- Govern the 5-step S&OP cycle (S&OP Cycle)

## 3) “All roles” usage

We discussed click-path playbooks for:

- Executive
- S&OP Coordinator
- Demand Planner
- Supply Planner
- Inventory Manager
- Finance Analyst
- Admin

See: [`role-playbooks.md`](role-playbooks.md)

## 4) ERP/WMS integration (later)

We discussed that GenXSOP can start standalone (manual entry / seeded sample data), and later integrate with ERP/WMS.

Three integration scenarios:

1. Read-only integration (ingest master data + actuals)
2. Publish-back integration (write approved plans to ERP)
3. Closed-loop (both)

See: [`integration/erp-wms-integration.md`](integration/erp-wms-integration.md)

## 5) Publishing governance (weekly + monthly)

We discussed readiness controls needed to safely publish plans into ERP:

- Publish readiness checklist
- Go/No-Go scorecard
- Two publish lanes (weekly and monthly)

See: [`integration/publish-readiness.md`](integration/publish-readiness.md)
