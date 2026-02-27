"""
Forecast Service — Service Layer (SRP / DIP)
Uses Strategy + Factory patterns for ML model selection.
"""
from typing import Optional, List
from datetime import date
import pandas as pd
from sqlalchemy.orm import Session

from app.repositories.forecast_repository import ForecastRepository
from app.repositories.demand_repository import DemandPlanRepository
from app.models.forecast import Forecast
from app.ml.factory import ForecastModelFactory
from app.ml.anomaly_detection import AnomalyDetector
from app.core.exceptions import EntityNotFoundException, InsufficientDataException, to_http_exception
from app.utils.events import get_event_bus, ForecastGeneratedEvent


class ForecastService:

    def __init__(self, db: Session):
        self._repo = ForecastRepository(db)
        self._demand_repo = DemandPlanRepository(db)
        self._bus = get_event_bus()

    def list_forecasts(
        self,
        product_id: Optional[int] = None,
        model_type: Optional[str] = None,
        period_from: Optional[date] = None,
        period_to: Optional[date] = None,
    ) -> List[Forecast]:
        return self._repo.list_filtered(
            product_id=product_id, model_type=model_type,
            period_from=period_from, period_to=period_to,
        )

    def get_forecast(self, forecast_id: int) -> Forecast:
        f = self._repo.get_by_id(forecast_id)
        if not f:
            raise to_http_exception(EntityNotFoundException("Forecast", forecast_id))
        return f

    def generate_forecast(
        self,
        product_id: int,
        model_type: Optional[str],
        horizon: int,
        user_id: int,
    ) -> List[Forecast]:
        """
        Generate a forecast using the Strategy + Factory pattern.
        Auto-selects the best model if model_type is None.
        """
        # Build training data from historical demand actuals
        history = self._demand_repo.get_with_actuals(product_id)
        if len(history) < 3:
            raise to_http_exception(
                InsufficientDataException(required=3, available=len(history), operation="forecast generation")
            )
        df = pd.DataFrame([
            {"ds": pd.Timestamp(h.period), "y": float(h.actual_qty)}
            for h in history
        ])

        # Factory selects strategy (auto or explicit)
        if model_type:
            context = ForecastModelFactory.create_context(model_type)
        else:
            context = ForecastModelFactory.create_context(
                ForecastModelFactory.get_best_strategy(len(history)).model_id
            )

        predictions = context.execute(df, horizon)
        created = []
        for pred in predictions:
            # Upsert: delete existing forecast for same product/model/period
            self._repo.delete_by_product_model_period(
                product_id, context.strategy.model_id, pred["period"]
            )
            forecast = Forecast(
                product_id=product_id,
                model_type=context.strategy.model_id,
                period=pred["period"],
                predicted_qty=pred["predicted_qty"],
                lower_bound=pred["lower_bound"],
                upper_bound=pred["upper_bound"],
                confidence=pred["confidence"],
                mape=pred.get("mape"),
            )
            created.append(self._repo.create(forecast))

        self._bus.publish(ForecastGeneratedEvent(
            product_id=product_id,
            model_type=context.strategy.model_id,
            horizon_months=horizon,
            records_created=len(created),
            user_id=user_id,
        ))
        return created

    def get_accuracy_metrics(self, product_id: Optional[int] = None) -> List[dict]:
        """Return MAPE accuracy metrics per model."""
        forecasts = self._repo.get_with_mape(product_id=product_id)
        model_stats: dict = {}
        for f in forecasts:
            key = f.model_type
            if key not in model_stats:
                model_stats[key] = {"mape_sum": 0.0, "count": 0}
            model_stats[key]["mape_sum"] += float(f.mape)
            model_stats[key]["count"] += 1
        return [
            {
                "model_type": model,
                "avg_mape": round(stats["mape_sum"] / stats["count"], 4),
                "sample_count": stats["count"],
            }
            for model, stats in model_stats.items()
        ]

    def detect_anomalies(self, product_id: int) -> List[dict]:
        """Run anomaly detection on historical demand for a product."""
        history = self._demand_repo.get_with_actuals(product_id)
        if len(history) < 6:
            return []
        values = [float(h.actual_qty) for h in history]
        periods = [str(h.period) for h in history]
        detector = AnomalyDetector()
        anomaly_indices = detector.detect(values)
        return [
            {
                "period": periods[i],
                "value": values[i],
                "severity": "high" if abs(values[i] - sum(values) / len(values)) > 2 * (sum((v - sum(values)/len(values))**2 for v in values)/len(values))**0.5 else "medium",
            }
            for i in anomaly_indices
        ]

    def list_models(self) -> List[dict]:
        """Return all available forecasting models."""
        return ForecastModelFactory.list_models()
