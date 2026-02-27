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
from typing import List, Dict, Any
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
    def forecast(self, df: pd.DataFrame, horizon: int) -> List[Dict[str, Any]]:
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

    def forecast(self, df: pd.DataFrame, horizon: int) -> List[Dict[str, Any]]:
        window = min(6, len(df))
        recent = df["y"].tail(window).values
        weights = np.arange(1, window + 1, dtype=float)
        weighted_avg = float(np.average(recent, weights=weights))
        trend = float(df["y"].iloc[-1] - df["y"].iloc[-2]) * 0.3 if len(df) >= 2 else 0.0
        std = float(df["y"].std()) if len(df) > 1 else weighted_avg * 0.1
        future_periods = self._build_future_periods(df, horizon)
        return [
            {
                "period": p,
                "predicted_qty": round(max(0.0, weighted_avg + trend * i * 0.5), 2),
                "lower_bound": round(max(0.0, weighted_avg + trend * i * 0.5 - 1.96 * std), 2),
                "upper_bound": round(weighted_avg + trend * i * 0.5 + 1.96 * std, 2),
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

    def forecast(self, df: pd.DataFrame, horizon: int) -> List[Dict[str, Any]]:
        if len(df) < 4:
            return MovingAverageStrategy().forecast(df, horizon)
        try:
            from statsmodels.tsa.holtwinters import ExponentialSmoothing
            model = ExponentialSmoothing(
                df["y"].values,
                trend="add",
                seasonal="add" if len(df) >= 24 else None,
                seasonal_periods=12 if len(df) >= 24 else None,
                damped_trend=True,
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
            return MovingAverageStrategy().forecast(df, horizon)


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

    def forecast(self, df: pd.DataFrame, horizon: int) -> List[Dict[str, Any]]:
        alpha = 0.35
        ewma = float(df["y"].ewm(alpha=alpha, adjust=False).mean().iloc[-1])
        trend = float(df["y"].diff().tail(3).mean()) if len(df) >= 4 else 0.0
        std = float(df["y"].std()) if len(df) > 1 else max(1.0, ewma * 0.1)
        future_periods = self._build_future_periods(df, horizon)
        return [
            {
                "period": p,
                "predicted_qty": round(max(0.0, ewma + trend * i * 0.4), 2),
                "lower_bound": round(max(0.0, ewma + trend * i * 0.4 - 1.64 * std), 2),
                "upper_bound": round(max(0.0, ewma + trend * i * 0.4 + 1.64 * std), 2),
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

    def forecast(self, df: pd.DataFrame, horizon: int) -> List[Dict[str, Any]]:
        if len(df) < 12:
            return EWMAStrategy().forecast(df, horizon)
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

    def forecast(self, df: pd.DataFrame, horizon: int) -> List[Dict[str, Any]]:
        if len(df) < self.min_data_months:
            return ExponentialSmoothingStrategy().forecast(df, horizon)

        try:
            from statsmodels.tsa.arima.model import ARIMA
            model = ARIMA(df["y"].astype(float).values, order=(1, 1, 1))
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
            return ExponentialSmoothingStrategy().forecast(df, horizon)


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

    def forecast(self, df: pd.DataFrame, horizon: int) -> List[Dict[str, Any]]:
        if len(df) < 12:
            return ExponentialSmoothingStrategy().forecast(df, horizon)
        try:
            from prophet import Prophet
            model = Prophet(
                yearly_seasonality=True,
                weekly_seasonality=False,
                daily_seasonality=False,
                seasonality_mode="multiplicative",
                changepoint_prior_scale=0.05,
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
            return ExponentialSmoothingStrategy().forecast(df, horizon)


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

    def execute(self, df: pd.DataFrame, horizon: int) -> List[Dict[str, Any]]:
        """Run the current strategy."""
        return self._strategy.forecast(df, horizon)
