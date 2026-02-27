# ADR-0006: Forecast Sandbox + User-Selected Demand Adoption

- **Status:** Accepted
- **Date:** 2026-02-27
- **Deciders:** GenXSOP engineering

## Context

Forecasting originally supported direct generation and storage of model output, with optional LLM model recommendation.

Planners requested a safer, experimentation-first workflow where they can:

1. Compare multiple statistical/ML model outputs side-by-side,
2. Use LLM explanations to understand tradeoffs,
3. Explicitly choose one preferred option,
4. Promote that option into demand planning.

This was needed to improve explainability, planner trust, and human control in the S&OP process.

## Decision

We adopt a **sandbox-first forecasting workflow** with **human-in-the-loop promotion**:

1. Add a non-destructive sandbox execution API:
   - `POST /api/v1/forecasting/sandbox/run`
2. Add explicit promotion API:
   - `POST /api/v1/forecasting/sandbox/promote`
3. Use LLM as advisor/comparator only (never autonomous committer):
   - Rank options + provide rationale
   - Deterministic fallback when LLM is unavailable/fails
4. Expand forecasting model catalog to improve comparison breadth:
   - `moving_average`, `ewma`, `exp_smoothing`, `seasonal_naive`, `arima`, `prophet`

Promotion writes selected forecasts into demand plans and preserves planner ownership by requiring explicit action.

## Consequences

### Positive

- Better planner trust through comparison + explainability.
- Reduced risk of blindly committing one model output.
- Stronger governance via explicit selection and promotion step.
- Improved flexibility with broader model library (incl. ARIMA, EWMA).

### Tradeoffs

- More UX and API complexity than a single “generate” endpoint.
- Higher compute footprint for multi-model sandbox runs.
- Requires tighter prompt/response guardrails for LLM comparator output.

### Guardrails

- LLM remains advisory; deterministic ranking fallback is mandatory.
- Promotion endpoint is role-protected and explicit.
- Forecast sandbox remains non-destructive until promotion is invoked.

## Related Artifacts

- `backend/app/services/forecast_service.py`
- `backend/app/services/forecast_advisor_service.py`
- `backend/app/routers/forecasting.py`
- `backend/app/ml/strategies.py`
- `backend/app/ml/factory.py`
- `frontend/src/pages/ForecastingPage.tsx`
- `docs/architecture/components-forecasting.md`
- `docs/forecasting-genxai-enhancements.md`
