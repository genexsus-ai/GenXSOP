# Forecasting Guide: Finding the Best Model and Parameters

This guide explains how to use GenXSOP forecasting APIs to:

1. Compare forecasting models fairly with backtesting
2. Tune model parameters using `parameter_grid`
3. Select and run the best model with the best parameter set

---

## 1) What `parameter_grid` does

Endpoint: `GET /api/v1/forecasting/model-comparison`

`parameter_grid` is a JSON object where:

- each key is a `model_id`
- each value is a list of parameter objects to test for that model

The service backtests each parameter set and returns:

- `best_params` for each model
- best metrics (`mape`, `wape`, `rmse`, etc.) for each model
- optional full `parameter_results` if `include_parameter_results=true`

The final ranking is done by the internal score:

- `score = mape + (wape * 0.25)`
- lower score is better

---

## 2) Supported models and tunable parameters

Use these model IDs in `models` and `parameter_grid`:

- `moving_average`
  - `window` (int, 2..12)
  - `trend_weight` (float, 0.0..1.0)
- `ewma`
  - `alpha` (float, 0.05..0.95)
  - `trend_weight` (float, 0.0..1.0)
- `exp_smoothing`
  - `damped_trend` (bool)
- `arima`
  - `p` (int, 0..3)
  - `d` (int, 0..2)
  - `q` (int, 0..3)
- `prophet`
  - `changepoint_prior_scale` (float, 0.001..0.5)
  - `seasonality_mode` (`multiplicative` or `additive`)
- `lstm` (PyTorch)
  - `lookback_window` (int, 3..24)
  - `hidden_size` (int, 8..256)
  - `num_layers` (int, 1..4)
  - `dropout` (float, 0.0..0.6)
  - `epochs` (int, 20..400)
  - `learning_rate` (float, 0.0001..0.1)

> Note: Out-of-range values are normalized by the backend to allowed bounds.

---

## 3) Parameter grid example (recommended)

### Example A: Tune `moving_average` and `ewma`

Use `--data-urlencode` so JSON is safely passed as query text.

```bash
curl -G "http://localhost:8000/api/v1/forecasting/model-comparison" \
  -H "Authorization: Bearer <YOUR_TOKEN>" \
  --data-urlencode "product_id=1" \
  --data-urlencode "test_months=6" \
  --data-urlencode "min_train_months=6" \
  --data-urlencode "models=moving_average" \
  --data-urlencode "models=ewma" \
  --data-urlencode "include_parameter_results=true" \
  --data-urlencode 'parameter_grid={
    "moving_average":[
      {"window":3,"trend_weight":0.2},
      {"window":6,"trend_weight":0.5},
      {"window":9,"trend_weight":0.8}
    ],
    "ewma":[
      {"alpha":0.2,"trend_weight":0.2},
      {"alpha":0.4,"trend_weight":0.5},
      {"alpha":0.6,"trend_weight":0.7}
    ]
  }'
```

### Example response shape (simplified)

```json
{
  "product_id": 1,
  "models": [
    {
      "rank": 1,
      "model_type": "ewma",
      "best_params": { "alpha": 0.4, "trend_weight": 0.5 },
      "mape": 8.31,
      "wape": 7.92,
      "score": 10.29,
      "parameter_results": [
        { "model_params": { "alpha": 0.2, "trend_weight": 0.2 }, "score": 11.02 },
        { "model_params": { "alpha": 0.4, "trend_weight": 0.5 }, "score": 10.29 }
      ]
    }
  ]
}
```

How to read it:

- `models[0]` is your best model for this product/window.
- `best_params` is the best parameter set for that model.

---

## 4) End-to-end workflow to find the best model

1. **Load enough history**
   - Keep at least 12+ months of actual demand for more stable rankings.
2. **Run baseline comparison first**
   - Call `/forecasting/model-comparison` without `parameter_grid`.
3. **Run focused tuning**
   - Add `parameter_grid` for top 2–3 models only.
4. **Review ranking + stability**
   - Primary: lowest `score`
   - Secondary: lower `mape`/`wape`, acceptable `bias`, higher `hit_rate`
5. **Generate production forecast with winning config**
   - Call `POST /api/v1/forecasting/generate` with `model_type` + `model_params`.
6. **Promote to demand planning**
   - Use `POST /api/v1/forecasting/promote` after planner review.

---

## 5) Run forecast with best params

Once you pick a winner from model-comparison, run generation with the same params.

```bash
curl -X POST "http://localhost:8000/api/v1/forecasting/generate?product_id=1&horizon=6&model_type=ewma" \
  -H "Authorization: Bearer <YOUR_TOKEN>" \
  --data-urlencode 'model_params={"alpha":0.4,"trend_weight":0.5}'
```

You should see those values reflected in:

- `diagnostics.selected_model_params` (generate response)
- `model_params` (forecast results endpoint)

---

## 6) Practical tips for users

- Start with small grids (3–5 combinations per model).
- Tune only a few models at a time.
- Use recent `test_months` that match your business horizon (for example 6).
- Re-run tuning when demand pattern changes (seasonality shift, promotions, channel change).
- If rankings are close, prefer the model with lower bias and better hit rate.

---

## 7) Common issues

- **422 Invalid JSON for `parameter_grid`**
  - Ensure valid JSON object text and proper escaping.
- **Insufficient data**
  - Add more historical actual demand points.
- **Unexpected parameter behavior**
  - Backend normalizes values to valid ranges.
