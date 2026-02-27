"""
Forecasting Router — Thin Controller (SRP / DIP)
Uses ForecastService which internally uses Strategy + Factory patterns.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date

from app.database import get_db
from app.models.user import User
from app.dependencies import get_current_user, require_roles
from app.services.forecast_service import ForecastService

router = APIRouter(prefix="/forecasting", tags=["AI Forecasting"])

PLANNER_ROLES = ["admin", "demand_planner", "supply_planner", "finance_analyst", "sop_coordinator"]


def get_forecast_service(db: Session = Depends(get_db)) -> ForecastService:
    return ForecastService(db)


@router.get("/models")
def list_models(
    service: ForecastService = Depends(get_forecast_service),
    _: User = Depends(get_current_user),
):
    """List all available forecasting models (Strategy registry)."""
    return service.list_models()


@router.post("/generate")
def generate_forecast(
    product_id: int,
    horizon: int = Query(6, ge=1, le=24),
    model_type: Optional[str] = None,
    service: ForecastService = Depends(get_forecast_service),
    current_user: User = Depends(require_roles(PLANNER_ROLES)),
):
    """Generate forecast using Strategy + Factory pattern. Auto-selects best model if model_type is None."""
    results = service.generate_forecast(
        product_id=product_id,
        model_type=model_type,
        horizon=horizon,
        user_id=current_user.id,
    )
    return {
        "product_id": product_id,
        "model_type": results[0].model_type if results else model_type,
        "horizon": horizon,
        "forecasts": [
            {
                "period": str(f.period),
                "predicted_qty": float(f.predicted_qty),
                "lower_bound": float(f.lower_bound) if f.lower_bound else None,
                "upper_bound": float(f.upper_bound) if f.upper_bound else None,
                "confidence": float(f.confidence) if f.confidence else None,
            }
            for f in results
        ],
    }


@router.get("/results")
def list_forecast_results(
    product_id: Optional[int] = None,
    model_type: Optional[str] = None,
    period_from: Optional[date] = None,
    period_to: Optional[date] = None,
    service: ForecastService = Depends(get_forecast_service),
    _: User = Depends(get_current_user),
):
    results = service.list_forecasts(
        product_id=product_id, model_type=model_type,
        period_from=period_from, period_to=period_to,
    )
    return [
        {
            "id": f.id,
            "product_id": f.product_id,
            "model_type": f.model_type,
            "period": str(f.period),
            "predicted_qty": float(f.predicted_qty),
            "lower_bound": float(f.lower_bound) if f.lower_bound else None,
            "upper_bound": float(f.upper_bound) if f.upper_bound else None,
            "confidence": float(f.confidence) if f.confidence else None,
            "mape": float(f.mape) if f.mape else None,
        }
        for f in results
    ]


@router.get("/accuracy")
def forecast_accuracy(
    product_id: Optional[int] = None,
    service: ForecastService = Depends(get_forecast_service),
    _: User = Depends(get_current_user),
):
    return service.get_accuracy_metrics(product_id=product_id)


@router.post("/anomalies/detect")
def detect_anomalies(
    product_id: int,
    service: ForecastService = Depends(get_forecast_service),
    current_user: User = Depends(require_roles(PLANNER_ROLES)),
):
    return service.detect_anomalies(product_id=product_id)
