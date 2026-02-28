# Forecasting Enhancements with GenXAI Advisor

## Overview

This document summarizes the recent forecasting improvements implemented in GenXSOP, including:

1. **GenXAI/OpenAI advisor integration** for model recommendation (advisor mode)
2. **Improved forecasting diagnostics** and richer accuracy metrics
3. **Enhanced forecasting UI visualizations**
4. **Test and validation coverage**
5. **Forecast result promotion flow into demand plans**

The objective was to improve forecasting quality, explainability, and operational usability while preserving deterministic fallback behavior.

---

## What Was Implemented

### 1) GenXAI Advisor Layer (Backend)

**File:** `backend/app/services/forecast_advisor_service.py`

Implemented a dedicated advisor service that:

- Uses GenXAI runtime (`AssistantAgent` + `AgentRuntime`) with OpenAI provider
- Reads API credentials from environment (`OPENAI_API_KEY`)
- Recommends one of supported models:
  - `moving_average`
  - `ewma`
  - `exp_smoothing`
  - `seasonal_naive`
  - `arima`
  - `prophet`
- Returns structured recommendation metadata:
  - `recommended_model`
  - `confidence`
  - `reason`
  - `advisor_enabled`
  - `fallback_used`
  - `warnings`

#### Safety / Guardrails

The advisor is **advisory-only** and safe by default:

- If user explicitly requests a model, that model is used directly.
- If `OPENAI_API_KEY` is missing, deterministic fallback is used.
- If GenXAI execution/parsing fails, deterministic fallback is used.
- Unsupported recommendations are rejected and fallback model is used.

---

### 2) Forecast Service Improvements (Backend)

**File:** `backend/app/services/forecast_service.py`

Added:

- `generate_forecast_with_diagnostics(...)`
- `promote_forecast_results_to_demand_plan(...)` for user-selected demand-plan adoption
- Backtest-style candidate scoring across available models
- Data quality flags generation (e.g., short history, missing months, volatility)
- Advisor-assisted model selection pipeline:
  1. Backtest-derived default model
  2. GenXAI advisor recommendation (if enabled)
  3. Deterministic fallback on failure

New diagnostics payload includes:

- `selected_model`
- `selection_reason`
- `advisor_confidence`
- `advisor_enabled`
- `fallback_used`
- `warnings`
- `history_months`
- `candidate_metrics`
- `data_quality_flags`

### Forecast result promotion payload

`promote_forecast_results_to_demand_plan(...)` returns:

- `product_id`
- `selected_model`
- `records_promoted`
- `periods[]`

#### Accuracy Metrics Upgrade

`get_accuracy_metrics(...)` now supports richer model-level metrics:

- `mape`
- `wape`
- `rmse`
- `mae`
- `bias`
- `hit_rate`
- `period_count`
- `sample_count`
- `avg_mape`

---

### 3) Forecasting API Enhancements

**File:** `backend/app/routers/forecasting.py`

`POST /api/v1/forecasting/generate` now returns:

- Existing forecast results
- Per-forecast `model_type`
- Top-level `diagnostics` object for advisor/model-selection traceability

This enables frontend explainability and better planner confidence in generated output.

Added new endpoint:

- `POST /api/v1/forecasting/promote`
  - Promotes selected forecast model output into demand planning records

---

### 4) Configuration Updates

**File:** `backend/app/config.py`

Added forecasting/LLM config keys:

- `OPENAI_API_KEY`
- `GENXAI_LLM_MODEL` (default: `gpt-4o-mini`)
- `GENXAI_LLM_TEMPERATURE` (default: `0.2`)
- `GENXAI_MAX_EXECUTION_TIME_SECONDS` (default: `20.0`)

---

### 5) Frontend Contract + Visualization Upgrades

#### Type updates

**File:** `frontend/src/types/index.ts`

- Forecast model type aligned to backend-supported models
  - `moving_average`, `ewma`, `exp_smoothing`, `seasonal_naive`, `arima`, `prophet`
- Added diagnostics types:
  - `ForecastDiagnostics`
  - `GenerateForecastResponse`
- Added promotion type:
  - `ForecastPromoteResponse`
- Extended `ForecastAccuracy` with `wape`, `sample_count`, `avg_mape`

#### Service updates

**File:** `frontend/src/services/forecastService.ts`

- `generateForecast(...)` now returns:
  - `forecasts`
  - `diagnostics`
- Accuracy normalization updated for richer backend metrics
- Added:
  - `promoteForecastResults(...)`

#### Forecasting page updates

**File:** `frontend/src/pages/ForecastingPage.tsx`

Added:

- **AI Advisor Decision card** (model, confidence, reason)
- **Promote to Demand Plan** action per selected managed forecast result
- **Forecast curve chart** with confidence band
- **Model quality chart** (MAPE / WAPE / Hit Rate)
- Updated model selector to supported models only

---

## Testing and Validation

### Added/updated tests

- **Backend:** `backend/tests/unit/test_forecast_advisor_service.py`
  - Explicit model usage behavior
  - LLM-disabled fallback behavior
  - Compare-options fallback ranking behavior

- **Backend:** `backend/tests/unit/test_ml_strategies.py`
  - EWMA strategy tests
  - Seasonal Naive strategy tests
  - ARIMA strategy tests

- **Frontend:** `frontend/src/services/forecastService.test.ts`
  - Generate response diagnostics mapping
  - Accuracy normalization verification

### Verification performed

- Frontend unit test (`vitest run`) ✅
- Frontend production build (`npm run build`) ✅
- Backend module compile (`python -m compileall`) ✅
- Backend advisor unit tests (`pytest`) ✅

---

## Operational Notes

- To enable LLM advisor behavior, set `OPENAI_API_KEY` in `backend/.env`.
- If key is absent or runtime fails, forecasting still works via deterministic model selection.
- Existing async forecast job flow remains compatible; it uses the updated forecast service logic.
