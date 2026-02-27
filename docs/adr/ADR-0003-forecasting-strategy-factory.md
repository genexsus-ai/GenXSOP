# ADR-0003: Forecasting extensibility via Strategy + Factory

**Status:** Accepted

## Context

Forecasting needs to support multiple algorithms (moving average, exponential smoothing, Prophet, etc.) and allow adding more over time.

We want to avoid:

- large `if/else` blocks in services,
- coupling forecast generation to a single library,
- modifying core service code for each new model.

## Decision

Use:

- **Strategy Pattern** for algorithms (`BaseForecastStrategy` + concrete strategies)
- **Factory Pattern** for registration/creation (`ForecastModelFactory`)

Selection behavior:

- If the caller passes `model_type`, create that strategy.
- Otherwise auto-select the best strategy based on history length.

## Consequences

### Positive

- New models can be added by implementing a new strategy and registering it.
- Service logic stays stable.
- Strategy objects can be unit-tested in isolation.

### Negative

- Strategy implementations may require heavy dependencies (e.g., Prophet). This increases install size and can increase cold start time.
- In-process model execution can be CPU-intensive; background execution may be needed as the product scales.

## References

- `backend/app/ml/strategies.py`
- `backend/app/ml/factory.py`
- `backend/app/services/forecast_service.py`
- `backend/app/routers/forecasting.py`
