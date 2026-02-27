"""
Unit Tests — ML Forecasting Strategy + Factory Patterns

Tests:
- Each concrete strategy produces correct output shape
- ForecastContext delegates to strategy correctly
- ForecastModelFactory creates correct strategies
- Factory auto-selection logic
- OCP: registering a new strategy at runtime
- AnomalyDetector unit tests
"""
import pytest
import pandas as pd
import numpy as np
from datetime import date
from dateutil.relativedelta import relativedelta

from app.ml.strategies import (
    MovingAverageStrategy,
    ExponentialSmoothingStrategy,
    ProphetStrategy,
    ForecastContext,
    BaseForecastStrategy,
)
from app.ml.factory import ForecastModelFactory
from app.ml.anomaly_detection import AnomalyDetector


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_df(months: int, base: float = 1000.0, noise: float = 50.0) -> pd.DataFrame:
    """Generate synthetic monthly demand data."""
    start = date(2023, 1, 1)
    rows = []
    for i in range(months):
        period = start + relativedelta(months=i)
        value = base + np.random.normal(0, noise)
        rows.append({"ds": pd.Timestamp(period), "y": max(0.0, value)})
    return pd.DataFrame(rows)


# ── Moving Average Strategy ───────────────────────────────────────────────────

class TestMovingAverageStrategy:

    def test_model_id(self):
        assert MovingAverageStrategy().model_id == "moving_average"

    def test_display_name(self):
        assert "Moving Average" in MovingAverageStrategy().display_name

    def test_min_data_months(self):
        assert MovingAverageStrategy().min_data_months == 3

    def test_forecast_returns_correct_horizon(self):
        df = make_df(12)
        result = MovingAverageStrategy().forecast(df, horizon=6)
        assert len(result) == 6

    def test_forecast_output_keys(self):
        df = make_df(6)
        result = MovingAverageStrategy().forecast(df, horizon=3)
        for item in result:
            assert "period" in item
            assert "predicted_qty" in item
            assert "lower_bound" in item
            assert "upper_bound" in item
            assert "confidence" in item

    def test_forecast_no_negative_values(self):
        df = make_df(6, base=10.0, noise=5.0)
        result = MovingAverageStrategy().forecast(df, horizon=6)
        for item in result:
            assert item["predicted_qty"] >= 0
            assert item["lower_bound"] >= 0

    def test_forecast_periods_are_sequential(self):
        df = make_df(6)
        result = MovingAverageStrategy().forecast(df, horizon=3)
        periods = [item["period"] for item in result]
        for i in range(1, len(periods)):
            assert periods[i] > periods[i - 1]

    def test_upper_bound_gte_lower_bound(self):
        df = make_df(12)
        result = MovingAverageStrategy().forecast(df, horizon=6)
        for item in result:
            assert item["upper_bound"] >= item["lower_bound"]


# ── Exponential Smoothing Strategy ───────────────────────────────────────────

class TestExponentialSmoothingStrategy:

    def test_model_id(self):
        assert ExponentialSmoothingStrategy().model_id == "exp_smoothing"

    def test_falls_back_to_moving_average_with_insufficient_data(self):
        df = make_df(3)
        result = ExponentialSmoothingStrategy().forecast(df, horizon=3)
        # Should still return results (fallback to MA)
        assert len(result) == 3

    def test_forecast_with_adequate_data(self):
        df = make_df(24)
        result = ExponentialSmoothingStrategy().forecast(df, horizon=6)
        assert len(result) == 6
        for item in result:
            assert item["predicted_qty"] >= 0


# ── Forecast Context ──────────────────────────────────────────────────────────

class TestForecastContext:

    def test_context_delegates_to_strategy(self):
        strategy = MovingAverageStrategy()
        context = ForecastContext(strategy)
        df = make_df(6)
        result = context.execute(df, horizon=3)
        assert len(result) == 3

    def test_context_strategy_switching(self):
        context = ForecastContext(MovingAverageStrategy())
        assert context.strategy.model_id == "moving_average"
        context.set_strategy(ExponentialSmoothingStrategy())
        assert context.strategy.model_id == "exp_smoothing"

    def test_context_strategy_property(self):
        strategy = MovingAverageStrategy()
        context = ForecastContext(strategy)
        assert context.strategy is strategy


# ── Factory Pattern ───────────────────────────────────────────────────────────

class TestForecastModelFactory:

    def test_create_moving_average(self):
        s = ForecastModelFactory.create("moving_average")
        assert isinstance(s, MovingAverageStrategy)

    def test_create_exp_smoothing(self):
        s = ForecastModelFactory.create("exp_smoothing")
        assert isinstance(s, ExponentialSmoothingStrategy)

    def test_create_unknown_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown forecast model"):
            ForecastModelFactory.create("nonexistent_model")

    def test_create_context_returns_forecast_context(self):
        ctx = ForecastModelFactory.create_context("moving_average")
        assert isinstance(ctx, ForecastContext)
        assert ctx.strategy.model_id == "moving_average"

    def test_list_models_returns_all_registered(self):
        models = ForecastModelFactory.list_models()
        ids = [m["id"] for m in models]
        assert "moving_average" in ids
        assert "exp_smoothing" in ids
        assert "prophet" in ids

    def test_list_models_has_required_keys(self):
        models = ForecastModelFactory.list_models()
        for m in models:
            assert "id" in m
            assert "name" in m
            assert "min_data_months" in m

    def test_auto_select_short_history(self):
        strategy = ForecastModelFactory.get_best_strategy(data_months=3)
        assert strategy.model_id == "moving_average"

    def test_auto_select_medium_history(self):
        strategy = ForecastModelFactory.get_best_strategy(data_months=15)
        assert strategy.model_id == "exp_smoothing"

    def test_auto_select_long_history(self):
        strategy = ForecastModelFactory.get_best_strategy(data_months=30)
        assert strategy.model_id == "prophet"

    def test_ocp_register_new_strategy(self):
        """OCP: Register a new strategy without modifying existing code."""
        class DummyStrategy(BaseForecastStrategy):
            @property
            def model_id(self): return "dummy"
            @property
            def display_name(self): return "Dummy"
            @property
            def min_data_months(self): return 1
            def forecast(self, df, horizon):
                return [{"period": date.today(), "predicted_qty": 0.0,
                         "lower_bound": 0.0, "upper_bound": 0.0,
                         "confidence": 50.0, "mape": None}] * horizon

        ForecastModelFactory.register("dummy", DummyStrategy)
        s = ForecastModelFactory.create("dummy")
        assert isinstance(s, DummyStrategy)
        # Cleanup
        del ForecastModelFactory._registry["dummy"]


# ── Anomaly Detector ──────────────────────────────────────────────────────────

class TestAnomalyDetector:

    def test_returns_empty_for_short_series(self):
        detector = AnomalyDetector()
        assert detector.detect([100, 200, 300]) == []

    def test_detects_obvious_spike(self):
        values = [100.0] * 10 + [5000.0]  # obvious spike at index 10
        detector = AnomalyDetector(z_threshold=2.0)
        anomalies = detector.detect(values)
        assert 10 in anomalies

    def test_no_anomalies_in_stable_series(self):
        values = [100.0 + i * 0.1 for i in range(20)]  # very stable
        detector = AnomalyDetector(z_threshold=3.0)
        anomalies = detector.detect(values)
        assert len(anomalies) == 0

    def test_returns_indices_not_values(self):
        values = [100.0] * 10 + [9999.0]
        detector = AnomalyDetector(z_threshold=2.0)
        anomalies = detector.detect(values)
        assert all(isinstance(i, int) for i in anomalies)

    def test_custom_threshold(self):
        values = [100.0] * 8 + [200.0, 300.0]
        strict = AnomalyDetector(z_threshold=1.0)
        lenient = AnomalyDetector(z_threshold=3.0)
        assert len(strict.detect(values)) >= len(lenient.detect(values))
