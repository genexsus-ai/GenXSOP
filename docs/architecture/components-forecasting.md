# Components (C4 L3) — Forecasting Domain

This document zooms into the **Forecasting** domain and shows the major backend components and their relationships.

> Why forecasting? It demonstrates GenXSOP’s core patterns clearly: **Router → Service → Repository**, plus **Strategy/Factory** for ML and **EventBus** for audit.

## Component diagram

```mermaid
flowchart TB
  %% External
  SPA["React SPA"]
  %% API layer
  subgraph API[FastAPI API]
    FR["routers/forecasting.py<br/>Forecasting Router"]
    DEP["dependencies.py<br/>get_current_user + require_roles"]
  end

  %% Domain/service layer
  subgraph Domain[Forecasting domain]
    FS["services/forecast_service.py<br/>ForecastService"]
    DPR["repositories/demand_repository.py<br/>DemandPlanRepository"]
    FOR["repositories/forecast_repository.py<br/>ForecastRepository"]
  end

  %% ML engine
  subgraph ML[ML Engine]
    FFactory["ml/factory.py<br/>ForecastModelFactory"]
    FContext["ml/strategies.py<br/>ForecastContext"]
    MAS[MovingAverageStrategy]
    ESS[ExponentialSmoothingStrategy]
    PS[ProphetStrategy]
    AD["ml/anomaly_detection.py<br/>AnomalyDetector"]
  end

  %% Cross-cutting
  subgraph XCut[Cross-cutting]
    BUS["utils/events.py<br/>EventBus"]
    AUD[AuditLogHandler]
    LOG[LoggingHandler]
  end

  %% Data
  DB[(Database)]
  ForecastTbl[(forecasts)]
  DemandTbl[(demand_plans)]
  AuditTbl[(audit_logs)]

  %% Flows
  SPA -->|HTTP /forecasting/*| FR
  FR --> DEP
  FR --> FS

  FS --> DPR
  DPR --> DemandTbl
  DemandTbl --> DB

  FS --> FFactory
  FFactory --> FContext
  FContext --> MAS
  FContext --> ESS
  FContext --> PS

  FS --> FOR
  FOR --> ForecastTbl
  ForecastTbl --> DB

  FS --> AD

  FS --> BUS
  BUS --> AUD
  BUS --> LOG
  AUD --> AuditTbl
  AuditTbl --> DB
```

## Primary endpoint flows

### Generate forecast (`POST /api/v1/forecasting/generate`)

```mermaid
sequenceDiagram
  autonumber
  participant SPA as React SPA
  participant R as Forecasting Router
  participant S as ForecastService
  participant DR as DemandPlanRepository
  participant F as ForecastModelFactory
  participant C as ForecastContext
  participant FR as ForecastRepository
  participant BUS as EventBus

  SPA->>R: POST /forecasting/generate
  R->>S: generate_forecast(product_id, model_type?, horizon, user_id)
  S->>DR: get_with_actuals(product_id)
  DR-->>S: demand history
  S->>F: create_context(selected_model)
  F-->>S: ForecastContext(strategy)
  S->>C: execute(df, horizon)
  C-->>S: predictions
  loop each predicted period
    S->>FR: upsert forecast rows
  end
  S->>BUS: publish(ForecastGeneratedEvent)
  S-->>R: forecasts
  R-->>SPA: JSON
```

### Detect anomalies (`POST /api/v1/forecasting/anomalies/detect`)

- Loads demand history with actuals.
- Runs `AnomalyDetector.detect(values)`.
- Returns indices/periods considered anomalous.

## Key design notes

- **Strategy interface** (`BaseForecastStrategy`) is the unit of extensibility.
- The **Factory registry** enables adding new models without changing service code.
- Publishing `ForecastGeneratedEvent` enables audit/telemetry without coupling.
