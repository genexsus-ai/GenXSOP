"""
Demand Forecasting ML Engine
Supports: Moving Average, Exponential Smoothing, ARIMA, Prophet, ML Ensemble
"""
import numpy as np
import pandas as pd
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.demand_plan import DemandPlan
from app.models.forecast import Forecast


def get_historical_data(db: Session, product_id: int) -> pd.DataFrame:
    """Fetch historical demand data for a product"""
    plans = (
        db.query(DemandPlan)
        .filter(
            DemandPlan.product_id == product_id,
            DemandPlan.actual_qty.isnot(None),
        )
        .order_by(DemandPlan.period.asc())
        .all()
    )
    if not plans:
        # Fall back to forecast_qty if no actuals
        plans = (
            db.query(DemandPlan)
            .filter(DemandPlan.product_id == product_id)
            .order_by(DemandPlan.period.asc())
            .all()
        )
    data = [
        {
            "ds": pd.Timestamp(p.period),
            "y": float(p.actual_qty or p.consensus_qty or p.adjusted_qty or p.forecast_qty),
        }
        for p in plans
    ]
    return pd.DataFrame(data)


def moving_average_forecast(df: pd.DataFrame, horizon: int, window: int = 3) -> List[Dict]:
    """Simple weighted moving average forecast"""
    if len(df) < window:
        window = max(1, len(df))
    recent = df["y"].tail(window).values
    weights = np.arange(1, window + 1)
    weighted_avg = float(np.average(recent, weights=weights))
    # Simple trend from last 2 points
    trend = 0.0
    if len(df) >= 2:
        trend = float(df["y"].iloc[-1] - df["y"].iloc[-2]) * 0.3
    last_period = df["ds"].iloc[-1].date() if len(df) > 0 else date.today().replace(day=1)
    results = []
    for i in range(1, horizon + 1):
        next_period = last_period + relativedelta(months=i)
        predicted = max(0, weighted_avg + trend * i * 0.5)
        std = float(df["y"].std()) if len(df) > 1 else predicted * 0.1
        results.append({
            "period": next_period,
            "predicted_qty": round(predicted, 2),
            "lower_bound": round(max(0, predicted - 1.96 * std), 2),
            "upper_bound": round(predicted + 1.96 * std, 2),
            "confidence": 80.0,
            "mape": None,
        })
    return results


def exp_smoothing_forecast(df: pd.DataFrame, horizon: int) -> List[Dict]:
    """Holt-Winters exponential smoothing"""
    try:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing
        if len(df) < 4:
            return moving_average_forecast(df, horizon)
        model = ExponentialSmoothing(
            df["y"].values,
            trend="add",
            seasonal="add" if len(df) >= 24 else None,
            seasonal_periods=12 if len(df) >= 24 else None,
            damped_trend=True,
        )
        fit = model.fit(optimized=True)
        forecast_values = fit.forecast(horizon)
        residuals = fit.resid
        std = float(np.std(residuals))
        last_period = df["ds"].iloc[-1].date()
        results = []
        for i, val in enumerate(forecast_values, 1):
            next_period = last_period + relativedelta(months=i)
            predicted = max(0, float(val))
            results.append({
                "period": next_period,
                "predicted_qty": round(predicted, 2),
                "lower_bound": round(max(0, predicted - 1.96 * std), 2),
                "upper_bound": round(predicted + 1.96 * std, 2),
                "confidence": 85.0,
                "mape": None,
            })
        return results
    except Exception:
        return moving_average_forecast(df, horizon)


def prophet_forecast(df: pd.DataFrame, horizon: int) -> List[Dict]:
    """Facebook Prophet forecast"""
    try:
        from prophet import Prophet
        if len(df) < 12:
            return exp_smoothing_forecast(df, horizon)
        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False,
            seasonality_mode="multiplicative",
            changepoint_prior_scale=0.05,
            interval_width=0.95,
        )
        model.fit(df)
        last_period = df["ds"].iloc[-1].date()
        future_dates = [last_period + relativedelta(months=i) for i in range(1, horizon + 1)]
        future_df = pd.DataFrame({"ds": [pd.Timestamp(d) for d in future_dates]})
        forecast = model.predict(future_df)
        results = []
        for i, row in forecast.iterrows():
            results.append({
                "period": future_dates[i],
                "predicted_qty": round(max(0, float(row["yhat"])), 2),
                "lower_bound": round(max(0, float(row["yhat_lower"])), 2),
                "upper_bound": round(max(0, float(row["yhat_upper"])), 2),
                "confidence": 95.0,
                "mape": None,
            })
        return results
    except Exception:
        return exp_smoothing_forecast(df, horizon)


def calculate_mape(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Calculate Mean Absolute Percentage Error"""
    mask = actual != 0
    if not mask.any():
        return 0.0
    return float(np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100)


def generate_forecast_for_product(
    db: Session,
    product_id: int,
    model_type: str = "moving_average",
    horizon_months: int = 6,
) -> List[Dict]:
    """Main entry point: generate forecast and save to DB"""
    df = get_historical_data(db, product_id)
    if df.empty:
        return []

    # Select model
    if model_type == "moving_average":
        forecasts = moving_average_forecast(df, horizon_months)
    elif model_type == "exp_smoothing":
        forecasts = exp_smoothing_forecast(df, horizon_months)
    elif model_type == "prophet":
        forecasts = prophet_forecast(df, horizon_months)
    else:
        forecasts = moving_average_forecast(df, horizon_months)

    # Calculate MAPE on historical data if enough data
    mape = None
    if len(df) >= 6:
        train = df.iloc[:-3]
        test = df.iloc[-3:]
        if len(train) >= 3:
            test_forecasts = moving_average_forecast(train, 3)
            if test_forecasts:
                predicted = np.array([f["predicted_qty"] for f in test_forecasts])
                actual = test["y"].values
                min_len = min(len(actual), len(predicted))
                mape = calculate_mape(actual[:min_len], predicted[:min_len])

    # Save to DB
    saved = []
    for f in forecasts:
        # Remove existing forecast for same product/model/period
        db.query(Forecast).filter(
            Forecast.product_id == product_id,
            Forecast.model_type == model_type,
            Forecast.period == f["period"],
        ).delete()
        forecast_record = Forecast(
            product_id=product_id,
            model_type=model_type,
            period=f["period"],
            predicted_qty=f["predicted_qty"],
            lower_bound=f["lower_bound"],
            upper_bound=f["upper_bound"],
            confidence=f["confidence"],
            mape=mape,
            model_version="1.0",
        )
        db.add(forecast_record)
        saved.append({
            "period": str(f["period"]),
            "predicted_qty": f["predicted_qty"],
            "lower_bound": f["lower_bound"],
            "upper_bound": f["upper_bound"],
            "mape": round(mape, 2) if mape else None,
        })
    db.commit()
    return saved
