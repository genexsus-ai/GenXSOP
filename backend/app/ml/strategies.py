"""
Forecasting Strategy Pattern — GoF Strategy Pattern

Principles applied:
- Strategy Pattern (GoF): Each forecasting algorithm is an interchangeable strategy.
- Open/Closed Principle (OCP): Add new models by creating a new strategy class, not modifying existing ones.
- Single Responsibility Principle (SRP): Each strategy class is responsible for exactly one algorithm.
- Liskov Substitution Principle (LSP): All strategies are substitutable for BaseForecastStrategy.
- Dependency Inversion Principle (DIP): ForecastContext depends on the abstraction, not concrete algorithms.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta


# ── Abstract Strategy ────────────────────────────────────────────────────────

class BaseForecastStrategy(ABC):
    """
    Abstract base class for all forecasting strategies.
    All concrete strategies MUST implement `forecast()`.
    """

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Unique identifier for this strategy (e.g., 'moving_average')."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name for UI display."""
        ...

    @property
    @abstractmethod
    def min_data_months(self) -> int:
        """Minimum months of history required to run this strategy."""
        ...

    @abstractmethod
    def forecast(self, df: pd.DataFrame, horizon: int, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Generate a forecast.

        Args:
            df: DataFrame with columns ['ds' (Timestamp), 'y' (float)]
            horizon: Number of months to forecast

        Returns:
            List of dicts with keys:
                period (date), predicted_qty (float),
                lower_bound (float), upper_bound (float),
                confidence (float), mape (float | None)
        """
        ...

    def _build_future_periods(self, df: pd.DataFrame, horizon: int) -> List[date]:
        """Helper: generate future monthly periods starting after the last data point."""
        last_period = df["ds"].iloc[-1].date() if len(df) > 0 else date.today().replace(day=1)
        return [last_period + relativedelta(months=i) for i in range(1, horizon + 1)]


# ── Concrete Strategy 1: Moving Average ──────────────────────────────────────

class MovingAverageStrategy(BaseForecastStrategy):
    """Weighted moving average with simple trend extrapolation."""

    @property
    def model_id(self) -> str:
        return "moving_average"

    @property
    def display_name(self) -> str:
        return "Moving Average"

    @property
    def min_data_months(self) -> int:
        return 3

    def forecast(self, df: pd.DataFrame, horizon: int, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        params = params or {}
        configured_window = int(params.get("window", 6)) if str(params.get("window", "")).strip() else 6
        configured_window = max(2, min(12, configured_window))
        trend_weight = float(params.get("trend_weight", 0.5))
        trend_weight = max(0.0, min(1.0, trend_weight))

        window = min(configured_window, len(df))
        recent = df["y"].tail(window).values
        weights = np.arange(1, window + 1, dtype=float)
        weighted_avg = float(np.average(recent, weights=weights))
        trend = float(df["y"].iloc[-1] - df["y"].iloc[-2]) * 0.3 if len(df) >= 2 else 0.0
        std = float(df["y"].std()) if len(df) > 1 else weighted_avg * 0.1
        future_periods = self._build_future_periods(df, horizon)
        return [
            {
                "period": p,
                "predicted_qty": round(max(0.0, weighted_avg + trend * i * trend_weight), 2),
                "lower_bound": round(max(0.0, weighted_avg + trend * i * trend_weight - 1.96 * std), 2),
                "upper_bound": round(weighted_avg + trend * i * trend_weight + 1.96 * std, 2),
                "confidence": 80.0,
                "mape": None,
            }
            for i, p in enumerate(future_periods, 1)
        ]


# ── Concrete Strategy 2: Exponential Smoothing ───────────────────────────────

class ExponentialSmoothingStrategy(BaseForecastStrategy):
    """Holt-Winters triple exponential smoothing (trend + seasonality)."""

    @property
    def model_id(self) -> str:
        return "exp_smoothing"

    @property
    def display_name(self) -> str:
        return "Exponential Smoothing (Holt-Winters)"

    @property
    def min_data_months(self) -> int:
        return 12

    def forecast(self, df: pd.DataFrame, horizon: int, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        params = params or {}
        if len(df) < 4:
            return MovingAverageStrategy().forecast(df, horizon, params=params)
        try:
            from statsmodels.tsa.holtwinters import ExponentialSmoothing
            damped_trend = bool(params.get("damped_trend", True))
            model = ExponentialSmoothing(
                df["y"].values,
                trend="add",
                seasonal="add" if len(df) >= 24 else None,
                seasonal_periods=12 if len(df) >= 24 else None,
                damped_trend=damped_trend,
            )
            fit = model.fit(optimized=True)
            forecast_values = fit.forecast(horizon)
            std = float(np.std(fit.resid))
            future_periods = self._build_future_periods(df, horizon)
            return [
                {
                    "period": p,
                    "predicted_qty": round(max(0.0, float(v)), 2),
                    "lower_bound": round(max(0.0, float(v) - 1.96 * std), 2),
                    "upper_bound": round(float(v) + 1.96 * std, 2),
                    "confidence": 85.0,
                    "mape": None,
                }
                for p, v in zip(future_periods, forecast_values)
            ]
        except Exception:
            return MovingAverageStrategy().forecast(df, horizon, params=params)


class EWMAStrategy(BaseForecastStrategy):
    """Exponentially weighted moving average baseline."""

    @property
    def model_id(self) -> str:
        return "ewma"

    @property
    def display_name(self) -> str:
        return "EWMA"

    @property
    def min_data_months(self) -> int:
        return 4

    def forecast(self, df: pd.DataFrame, horizon: int, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        params = params or {}
        alpha = float(params.get("alpha", 0.35))
        alpha = max(0.05, min(0.95, alpha))
        trend_weight = float(params.get("trend_weight", 0.4))
        trend_weight = max(0.0, min(1.0, trend_weight))
        ewma = float(df["y"].ewm(alpha=alpha, adjust=False).mean().iloc[-1])
        trend = float(df["y"].diff().tail(3).mean()) if len(df) >= 4 else 0.0
        std = float(df["y"].std()) if len(df) > 1 else max(1.0, ewma * 0.1)
        future_periods = self._build_future_periods(df, horizon)
        return [
            {
                "period": p,
                "predicted_qty": round(max(0.0, ewma + trend * i * trend_weight), 2),
                "lower_bound": round(max(0.0, ewma + trend * i * trend_weight - 1.64 * std), 2),
                "upper_bound": round(max(0.0, ewma + trend * i * trend_weight + 1.64 * std), 2),
                "confidence": 82.0,
                "mape": None,
            }
            for i, p in enumerate(future_periods, 1)
        ]


class SeasonalNaiveStrategy(BaseForecastStrategy):
    """Seasonal naive baseline using prior year values."""

    @property
    def model_id(self) -> str:
        return "seasonal_naive"

    @property
    def display_name(self) -> str:
        return "Seasonal Naive"

    @property
    def min_data_months(self) -> int:
        return 12

    def forecast(self, df: pd.DataFrame, horizon: int, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if len(df) < 12:
            return EWMAStrategy().forecast(df, horizon, params=params)
        y = df["y"].values
        std = float(df["y"].std()) if len(df) > 1 else max(1.0, float(np.mean(y)) * 0.1)
        future_periods = self._build_future_periods(df, horizon)
        vals = []
        for i in range(1, horizon + 1):
            idx = -12 + ((i - 1) % 12)
            vals.append(float(y[idx]))
        return [
            {
                "period": p,
                "predicted_qty": round(max(0.0, v), 2),
                "lower_bound": round(max(0.0, v - 1.64 * std), 2),
                "upper_bound": round(max(0.0, v + 1.64 * std), 2),
                "confidence": 78.0,
                "mape": None,
            }
            for p, v in zip(future_periods, vals)
        ]


class ARIMAStrategy(BaseForecastStrategy):
    """ARIMA strategy with guarded fallback behavior."""

    @property
    def model_id(self) -> str:
        return "arima"

    @property
    def display_name(self) -> str:
        return "ARIMA"

    @property
    def min_data_months(self) -> int:
        return 12

    def forecast(self, df: pd.DataFrame, horizon: int, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        params = params or {}
        if len(df) < self.min_data_months:
            return ExponentialSmoothingStrategy().forecast(df, horizon, params=params)

        try:
            from statsmodels.tsa.arima.model import ARIMA
            p = int(params.get("p", 1)) if str(params.get("p", "")).strip() else 1
            d = int(params.get("d", 1)) if str(params.get("d", "")).strip() else 1
            q = int(params.get("q", 1)) if str(params.get("q", "")).strip() else 1
            p = max(0, min(3, p))
            d = max(0, min(2, d))
            q = max(0, min(3, q))
            model = ARIMA(df["y"].astype(float).values, order=(p, d, q))
            fit = model.fit()
            pred = fit.get_forecast(steps=horizon)
            vals = pred.predicted_mean
            ci = pred.conf_int(alpha=0.05)
            future_periods = self._build_future_periods(df, horizon)
            return [
                {
                    "period": p,
                    "predicted_qty": round(max(0.0, float(vals[i])), 2),
                    "lower_bound": round(max(0.0, float(ci[i][0])), 2),
                    "upper_bound": round(max(0.0, float(ci[i][1])), 2),
                    "confidence": 88.0,
                    "mape": None,
                }
                for i, p in enumerate(future_periods)
            ]
        except Exception:
            return ExponentialSmoothingStrategy().forecast(df, horizon, params=params)


# ── Concrete Strategy 3: Prophet ─────────────────────────────────────────────

class ProphetStrategy(BaseForecastStrategy):
    """Facebook Prophet time series model."""

    @property
    def model_id(self) -> str:
        return "prophet"

    @property
    def display_name(self) -> str:
        return "Prophet"

    @property
    def min_data_months(self) -> int:
        return 24

    def forecast(self, df: pd.DataFrame, horizon: int, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        params = params or {}
        if len(df) < 12:
            return ExponentialSmoothingStrategy().forecast(df, horizon, params=params)
        try:
            from prophet import Prophet
            changepoint_prior_scale = float(params.get("changepoint_prior_scale", 0.05))
            changepoint_prior_scale = max(0.001, min(0.5, changepoint_prior_scale))
            seasonality_mode = str(params.get("seasonality_mode", "multiplicative"))
            if seasonality_mode not in {"multiplicative", "additive"}:
                seasonality_mode = "multiplicative"
            model = Prophet(
                yearly_seasonality=True,
                weekly_seasonality=False,
                daily_seasonality=False,
                seasonality_mode=seasonality_mode,
                changepoint_prior_scale=changepoint_prior_scale,
                interval_width=0.95,
            )
            model.fit(df)
            future_periods = self._build_future_periods(df, horizon)
            future_df = pd.DataFrame({"ds": [pd.Timestamp(p) for p in future_periods]})
            forecast = model.predict(future_df)
            return [
                {
                    "period": future_periods[i],
                    "predicted_qty": round(max(0.0, float(row["yhat"])), 2),
                    "lower_bound": round(max(0.0, float(row["yhat_lower"])), 2),
                    "upper_bound": round(max(0.0, float(row["yhat_upper"])), 2),
                    "confidence": 95.0,
                    "mape": None,
                }
                for i, (_, row) in enumerate(forecast.iterrows())
            ]
        except Exception:
            return ExponentialSmoothingStrategy().forecast(df, horizon, params=params)


# ── Context (uses a strategy) ─────────────────────────────────────────────────

class ForecastContext:
    """
    Context class that executes a forecasting strategy.
    Decouples the caller from the concrete algorithm.
    """

    def __init__(self, strategy: BaseForecastStrategy):
        self._strategy = strategy

    @property
    def strategy(self) -> BaseForecastStrategy:
        return self._strategy

    def set_strategy(self, strategy: BaseForecastStrategy) -> None:
        """Allow runtime strategy switching."""
        self._strategy = strategy

    def execute(self, df: pd.DataFrame, horizon: int, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Run the current strategy."""
        return self._strategy.forecast(df, horizon, params=params)
