# Data Model

This document summarizes the persisted domain entities implemented under `backend/app/models/*`.

## Entity list

- `User` (`users`)
- `Category` (`categories`)
- `Product` (`products`)
- `DemandPlan` (`demand_plans`)
- `SupplyPlan` (`supply_plans`)
- `Inventory` (`inventory`)
- `Forecast` (`forecasts`)
- `Scenario` (`scenarios`)
- `SOPCycle` (`sop_cycles`)
- `KPIMetric` (`kpi_metrics`)
- `Comment` (`comments`)
- `AuditLog` (`audit_logs`)

## ER diagram (logical)

```mermaid
erDiagram
  USERS {
    int id PK
    string email
    string hashed_password
    string full_name
    string role
    string department
    bool is_active
    datetime created_at
    datetime updated_at
  }

  CATEGORIES {
    int id PK
    string name
    int parent_id FK
    int level
  }

  PRODUCTS {
    int id PK
    string sku
    string name
    int category_id FK
    string product_family
    decimal unit_cost
    decimal selling_price
    int lead_time_days
    string status
  }

  DEMAND_PLANS {
    int id PK
    int product_id FK
    date period
    string region
    string channel
    decimal forecast_qty
    decimal adjusted_qty
    decimal actual_qty
    decimal consensus_qty
    string status
    int created_by FK
    int approved_by FK
    int version
  }

  SUPPLY_PLANS {
    int id PK
    int product_id FK
    date period
    string location
    decimal planned_prod_qty
    decimal capacity_max
    string status
    int created_by FK
    int version
  }

  INVENTORY {
    int id PK
    int product_id FK
    string location
    decimal on_hand_qty
    decimal safety_stock
    decimal reorder_point
    decimal days_of_supply
    string status
  }

  FORECASTS {
    int id PK
    int product_id FK
    string model_type
    date period
    decimal predicted_qty
    decimal lower_bound
    decimal upper_bound
    decimal confidence
    decimal mape
  }

  SCENARIOS {
    int id PK
    string name
    string scenario_type
    string parameters
    string results
    decimal revenue_impact
    string status
    int created_by FK
    int approved_by FK
  }

  SOP_CYCLES {
    int id PK
    string cycle_name
    date period
    int current_step
    string overall_status
    int step_1_owner_id FK
    int step_2_owner_id FK
    int step_3_owner_id FK
    int step_4_owner_id FK
    int step_5_owner_id FK
  }

  KPI_METRICS {
    int id PK
    string metric_name
    string metric_category
    date period
    decimal value
    decimal target
    string trend
  }

  COMMENTS {
    int id PK
    string entity_type
    int entity_id
    int user_id FK
    int parent_id FK
    string content
  }

  AUDIT_LOGS {
    int id PK
    int user_id FK
    string action
    string entity_type
    int entity_id
    string old_values
    string new_values
    datetime created_at
  }

  %% Relationships
  CATEGORIES ||--o{ CATEGORIES : parent
  CATEGORIES ||--o{ PRODUCTS : categorizes
  PRODUCTS ||--o{ DEMAND_PLANS : has
  PRODUCTS ||--o{ SUPPLY_PLANS : has
  PRODUCTS ||--o{ INVENTORY : has
  PRODUCTS ||--o{ FORECASTS : has

  USERS ||--o{ DEMAND_PLANS : created_by
  USERS ||--o{ DEMAND_PLANS : approved_by
  USERS ||--o{ SUPPLY_PLANS : created_by
  USERS ||--o{ SCENARIOS : created_by
  USERS ||--o{ SCENARIOS : approved_by
  USERS ||--o{ SOP_CYCLES : owns_steps
  USERS ||--o{ COMMENTS : authored
  USERS ||--o{ AUDIT_LOGS : performed
  COMMENTS ||--o{ COMMENTS : replies
```

## Notes / constraints

- Several tables conceptually have uniqueness constraints by `(product_id, period, version, ...)` (as described in the design doc). In the current ORM models, these uniqueness constraints are not explicitly declared; they may be handled via migrations or left for later.
- `Comment` is polymorphic via `(entity_type, entity_id)` rather than strict foreign keys to each domain entity.
- `AuditLog` records entity mutations via the Observer/EventBus.
