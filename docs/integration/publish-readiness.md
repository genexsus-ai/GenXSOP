# Publish Readiness & Go/No-Go Scorecard

This document defines recommended controls before publishing plans from GenXSOP back into an ERP.

It supports both:

- **Weekly** publishing (execution-near)
- **Monthly** publishing (mid/long-range)

## 1) Publish lanes (scope)

- **Weekly lane:** next 4–8 weeks (often with a 1–2 week freeze)
- **Monthly lane:** next 6–18 months (directional planning)

## 2) Readiness checklist (must-pass gates)

### A) Data integrity gates

- Product master complete (SKU/UoM/category/lead time/cost/price as needed)
- Inventory snapshots are current within SLA
- Demand actuals refresh is current within SLA
- Calendar alignment validated (weeks/months/fiscal periods)

### B) Governance gates

- Demand plans approved for the publish horizon
- Supply plans approved for the publish horizon
- Scenario lock (if scenarios are used): one approved scenario tagged as operating plan
- S&OP cycle step gates met for the publish lane

### C) Publishing safety gates

- Frozen window respected
- Version stamping enabled (plan version ID + timestamp)
- Audit + rollback procedures in place

If any of the above fails → **No-Go**.

## 3) Plan quality thresholds (recommended)

Set thresholds by item class (A/B/C) and lane.

Example thresholds:

| Metric | Weekly lane (tighter) | Monthly lane (looser) |
|---|---:|---:|
| MAPE (A items) | ≤ 15–20% | ≤ 20–30% |
| Bias (A items) | within ±5% | within ±8–10% |
| Supply feasibility | no unresolved “red” constraints in frozen window | constraints must have actions |
| Inventory risk | no unmanaged critical stockouts | stockout risks acceptable with plan |

## 4) Go/No-Go scorecard

### Pass/Fail sections

- **Governance:** must pass
- **Data readiness:** must pass
- **Safety rules:** must pass

### Scored section

Score each (0/1):

1. Accuracy threshold met (key items)
2. Bias threshold met (key items)
3. Supply feasibility met
4. Inventory risk acceptable

Suggested rule:

- **Weekly publish:** requires 4/4
- **Monthly publish:** requires 3/4

Decision logic:

- If any must-pass section fails → **No-Go**
- Else if weekly and monthly meet thresholds → **Go (both)**
- Else → **Go (weekly only)** or **Go (monthly only)** depending on which lane qualifies
