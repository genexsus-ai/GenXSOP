"""
Forecasting Router — Thin Controller (SRP / DIP)
Uses ForecastService which internally uses Strategy + Factory patterns.
"""
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date
import json

from app.database import get_db
from app.models.user import User
from app.dependencies import get_current_user, require_roles
from app.schemas.forecast_consensus import (
    ForecastConsensusCreate,
    ForecastConsensusUpdate,
    ForecastConsensusApproveRequest,
    ForecastConsensusResponse,
)
from app.services.forecast_consensus_service import ForecastConsensusService
from app.services.forecast_service import ForecastService
from app.services.forecast_job_service import forecast_job_service

router = APIRouter(prefix="/forecasting", tags=["AI Forecasting"])

PLANNER_ROLES = ["admin", "demand_planner", "supply_planner", "finance_analyst", "sop_coordinator"]
OPS_ROLES = ["admin", "sop_coordinator", "executive"]


def get_forecast_service(db: Session = Depends(get_db)) -> ForecastService:
    return ForecastService(db)


def get_forecast_consensus_service(db: Session = Depends(get_db)) -> ForecastConsensusService:
    return ForecastConsensusService(db)


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
    payload = service.generate_forecast_with_diagnostics(
        product_id=product_id,
        model_type=model_type,
        horizon=horizon,
        user_id=current_user.id,
    )
    results = payload["forecasts"]
    return {
        "product_id": product_id,
        "model_type": results[0].model_type if results else model_type,
        "horizon": horizon,
        "diagnostics": payload.get("diagnostics", {}),
        "forecasts": [
            {
                "period": str(f.period),
                "predicted_qty": float(f.predicted_qty),
                "lower_bound": float(f.lower_bound) if f.lower_bound else None,
                "upper_bound": float(f.upper_bound) if f.upper_bound else None,
                "confidence": float(f.confidence) if f.confidence else None,
                "model_type": f.model_type,
            }
            for f in results
        ],
    }


@router.post("/recommendation")
def recommend_forecast_model(
    product_id: int,
    model_type: Optional[str] = None,
    service: ForecastService = Depends(get_forecast_service),
    _: User = Depends(require_roles(PLANNER_ROLES)),
):
    """Get GenXAI advisor recommendation diagnostics without generating forecast records."""
    payload = service.recommend_model(product_id=product_id, model_type=model_type)
    return {
        "product_id": product_id,
        "diagnostics": payload.get("diagnostics", {}),
    }


@router.post("/generate-job")
def generate_forecast_job(
    product_id: int,
    horizon: int = Query(6, ge=1, le=24),
    model_type: Optional[str] = None,
    current_user: User = Depends(require_roles(PLANNER_ROLES)),
):
    """
    Enqueue asynchronous forecast generation job.
    Returns immediately with a job identifier.
    """
    job = forecast_job_service.enqueue_forecast(
        product_id=product_id,
        horizon=horizon,
        model_type=model_type,
        requested_by=current_user.id,
    )
    return {
        "job_id": job.job_id,
        "status": job.status,
        "product_id": job.product_id,
        "horizon": job.horizon,
        "model_type": job.model_type,
        "requested_by": job.requested_by,
        "created_at": job.created_at.isoformat(),
    }


@router.get("/jobs")
def list_forecast_jobs(
    limit: int = Query(50, ge=1, le=200),
    _: User = Depends(require_roles(OPS_ROLES)),
):
    """List recent forecast async jobs for operational visibility."""
    jobs = forecast_job_service.list_jobs(limit=limit)
    return [
        {
            "job_id": job.job_id,
            "status": job.status,
            "product_id": job.product_id,
            "horizon": job.horizon,
            "model_type": job.model_type,
            "requested_by": job.requested_by,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "error": job.error,
        }
        for job in jobs
    ]


@router.post("/jobs/{job_id}/cancel")
def cancel_forecast_job(
    job_id: str,
    _: User = Depends(require_roles(OPS_ROLES)),
):
    """Cancel a queued/running forecast job."""
    job = forecast_job_service.cancel_job(job_id)
    if not job:
        return {"job_id": job_id, "status": "not_found"}
    return {
        "job_id": job.job_id,
        "status": job.status,
        "error": job.error,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


@router.post("/jobs/{job_id}/retry")
def retry_forecast_job(
    job_id: str,
    _: User = Depends(require_roles(OPS_ROLES)),
):
    """Retry a failed/cancelled forecast job as a new queued job."""
    job = forecast_job_service.retry_job(job_id)
    if not job:
        return {"job_id": job_id, "status": "not_found"}
    return {
        "job_id": job.job_id,
        "status": job.status,
        "product_id": job.product_id,
        "horizon": job.horizon,
        "model_type": job.model_type,
        "requested_by": job.requested_by,
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }


@router.get("/jobs/metrics")
def forecast_job_metrics(
    _: User = Depends(require_roles(OPS_ROLES)),
):
    """Operational metrics for async forecast jobs."""
    return forecast_job_service.get_job_metrics()


@router.post("/jobs/cleanup")
def cleanup_forecast_jobs(
    retention_days: Optional[int] = Query(None, ge=1, le=3650),
    current_user: User = Depends(require_roles(OPS_ROLES)),
):
    """Cleanup completed/failed/cancelled jobs older than retention policy."""
    return forecast_job_service.cleanup_old_jobs(
        retention_days=retention_days,
        requested_by=current_user.id,
    )


@router.get("/jobs/{job_id}")
def get_forecast_job(
    job_id: str,
    _: User = Depends(get_current_user),
):
    """Get async forecast job status and result payload (if completed)."""
    job = forecast_job_service.get_job(job_id)
    if not job:
        return {"job_id": job_id, "status": "not_found"}

    result_payload = None
    if job.result_json:
        try:
            result_payload = json.loads(job.result_json)
        except json.JSONDecodeError:
            result_payload = {"raw": job.result_json}

    return {
        "job_id": job.job_id,
        "status": job.status,
        "product_id": job.product_id,
        "horizon": job.horizon,
        "model_type": job.model_type,
        "requested_by": job.requested_by,
        "created_at": job.created_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "error": job.error,
        "result": result_payload,
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
    def _parse_features(raw: Optional[str]) -> dict:
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}

    return [
        ({
            "id": f.id,
            "product_id": f.product_id,
            "model_type": f.model_type,
            "period": str(f.period),
            "predicted_qty": float(f.predicted_qty),
            "lower_bound": float(f.lower_bound) if f.lower_bound else None,
            "upper_bound": float(f.upper_bound) if f.upper_bound else None,
            "confidence": float(f.confidence) if f.confidence else None,
            "mape": float(f.mape) if f.mape else None,
        } | {
            "run_audit_id": _parse_features(f.features_used).get("run_audit_id"),
            "selection_reason": _parse_features(f.features_used).get("selection_reason"),
            "advisor_confidence": _parse_features(f.features_used).get("advisor_confidence"),
            "advisor_enabled": _parse_features(f.features_used).get("advisor_enabled"),
            "fallback_used": _parse_features(f.features_used).get("fallback_used"),
            "warnings": _parse_features(f.features_used).get("warnings"),
        })
        for f in results
    ]


@router.delete("/results/{forecast_id}", status_code=204)
def delete_forecast_result(
    forecast_id: int,
    service: ForecastService = Depends(get_forecast_service),
    _: User = Depends(require_roles(PLANNER_ROLES)),
):
    service.delete_forecast(forecast_id)
    return Response(status_code=204)


@router.delete("/results/by-product/{product_id}")
def delete_forecast_results_by_product(
    product_id: int,
    service: ForecastService = Depends(get_forecast_service),
    _: User = Depends(require_roles(PLANNER_ROLES)),
):
    deleted_counts = service.delete_forecasts_by_product(product_id)
    return {
        "product_id": product_id,
        # Backward-compatible field used by existing UI.
        "deleted": deleted_counts["forecasts_deleted"],
        "forecasts_deleted": deleted_counts["forecasts_deleted"],
        "consensus_deleted": deleted_counts["consensus_deleted"],
    }


@router.get("/accuracy")
def forecast_accuracy(
    product_id: Optional[int] = None,
    service: ForecastService = Depends(get_forecast_service),
    _: User = Depends(get_current_user),
):
    return service.get_accuracy_metrics(product_id=product_id)


@router.get("/accuracy/drift-alerts")
def forecast_accuracy_drift_alerts(
    threshold_pct: float = Query(10.0, ge=0.0, le=100.0),
    min_points: int = Query(6, ge=3, le=60),
    service: ForecastService = Depends(get_forecast_service),
    _: User = Depends(get_current_user),
):
    """Detect month-over-month forecast degradation alerts."""
    return service.get_accuracy_drift_alerts(
        threshold_pct=threshold_pct,
        min_points=min_points,
    )


@router.post("/anomalies/detect")
def detect_anomalies(
    product_id: int,
    service: ForecastService = Depends(get_forecast_service),
    current_user: User = Depends(require_roles(PLANNER_ROLES)),
):
    return service.detect_anomalies(product_id=product_id)


@router.post("/promote")
def promote_forecast_results(
    product_id: int,
    selected_model: str,
    horizon: int = Query(6, ge=1, le=24),
    notes: Optional[str] = None,
    service: ForecastService = Depends(get_forecast_service),
    current_user: User = Depends(require_roles(PLANNER_ROLES)),
):
    """Promote selected forecast model results to demand plan records."""
    return service.promote_forecast_results_to_demand_plan(
        product_id=product_id,
        selected_model=selected_model,
        horizon=horizon,
        user_id=current_user.id,
        notes=notes,
    )


@router.get("/consensus", response_model=List[ForecastConsensusResponse])
def list_consensus_records(
    product_id: Optional[int] = None,
    forecast_run_audit_id: Optional[int] = None,
    status: Optional[str] = None,
    period_from: Optional[date] = None,
    period_to: Optional[date] = None,
    service: ForecastConsensusService = Depends(get_forecast_consensus_service),
    _: User = Depends(get_current_user),
):
    return service.list_consensus(
        product_id=product_id,
        forecast_run_audit_id=forecast_run_audit_id,
        status=status,
        period_from=period_from,
        period_to=period_to,
    )


@router.post("/consensus", response_model=ForecastConsensusResponse, status_code=201)
def create_consensus_record(
    data: ForecastConsensusCreate,
    service: ForecastConsensusService = Depends(get_forecast_consensus_service),
    current_user: User = Depends(require_roles(PLANNER_ROLES)),
):
    return service.create_consensus(data=data, user_id=current_user.id)


@router.patch("/consensus/{consensus_id}", response_model=ForecastConsensusResponse)
def update_consensus_record(
    consensus_id: int,
    data: ForecastConsensusUpdate,
    service: ForecastConsensusService = Depends(get_forecast_consensus_service),
    current_user: User = Depends(require_roles(PLANNER_ROLES)),
):
    return service.update_consensus(
        consensus_id=consensus_id,
        data=data,
        user_id=current_user.id,
    )


@router.post("/consensus/{consensus_id}/approve", response_model=ForecastConsensusResponse)
def approve_consensus_record(
    consensus_id: int,
    body: ForecastConsensusApproveRequest,
    service: ForecastConsensusService = Depends(get_forecast_consensus_service),
    current_user: User = Depends(require_roles(OPS_ROLES)),
):
    return service.approve_consensus(
        consensus_id=consensus_id,
        body=body,
        approver_id=current_user.id,
    )
