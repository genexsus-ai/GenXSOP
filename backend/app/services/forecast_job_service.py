"""
Forecast Job Service

Provides a lightweight async job orchestration layer for forecast generation.

Note:
- This is an in-process implementation intended as an enterprise transition step.
- For full production scale, migrate this interface to a durable queue (Celery/RQ + Redis/RabbitMQ).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
from typing import Optional, List
from uuid import uuid4

from app.database import SessionLocal
from app.models.forecast_job import ForecastJob
from app.services.forecast_service import ForecastService


class ForecastJobService:
    def __init__(self, max_workers: int = 2):
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="forecast-worker")

    def enqueue_forecast(
        self,
        *,
        product_id: int,
        horizon: int,
        model_type: Optional[str],
        requested_by: int,
    ) -> ForecastJob:
        db = SessionLocal()
        try:
            job = ForecastJob(
                job_id=str(uuid4()),
                status="queued",
                product_id=product_id,
                horizon=horizon,
                model_type=model_type,
                requested_by=requested_by,
            )
            db.add(job)
            db.commit()
            db.refresh(job)
        finally:
            db.close()

        self._executor.submit(self._run_forecast_job, job.job_id)
        return job

    def get_job(self, job_id: str) -> Optional[ForecastJob]:
        db = SessionLocal()
        try:
            return db.query(ForecastJob).filter(ForecastJob.job_id == job_id).first()
        finally:
            db.close()

    def list_jobs(self, limit: int = 50) -> List[ForecastJob]:
        db = SessionLocal()
        try:
            return (
                db.query(ForecastJob)
                .order_by(ForecastJob.created_at.desc())
                .limit(limit)
                .all()
            )
        finally:
            db.close()

    def cancel_job(self, job_id: str) -> Optional[ForecastJob]:
        db = SessionLocal()
        try:
            job = db.query(ForecastJob).filter(ForecastJob.job_id == job_id).first()
            if not job:
                return None
            if job.status in {"queued", "running"}:
                job.status = "cancelled"
                job.completed_at = datetime.utcnow()
                job.error = "Cancelled by user"
                db.commit()
                db.refresh(job)
            return job
        finally:
            db.close()

    def retry_job(self, job_id: str) -> Optional[ForecastJob]:
        db = SessionLocal()
        try:
            source_job = db.query(ForecastJob).filter(ForecastJob.job_id == job_id).first()
            if not source_job:
                return None
            if source_job.status not in {"failed", "cancelled"}:
                return source_job

            new_job = ForecastJob(
                job_id=str(uuid4()),
                status="queued",
                product_id=source_job.product_id,
                horizon=source_job.horizon,
                model_type=source_job.model_type,
                requested_by=source_job.requested_by,
            )
            db.add(new_job)
            db.commit()
            db.refresh(new_job)
        finally:
            db.close()

        self._executor.submit(self._run_forecast_job, new_job.job_id)
        return new_job

    def _run_forecast_job(self, job_id: str) -> None:
        db = SessionLocal()
        try:
            job = db.query(ForecastJob).filter(ForecastJob.job_id == job_id).first()
            if not job:
                return
            if job.status == "cancelled":
                return

            job.status = "running"
            job.started_at = datetime.utcnow()
            db.commit()

            service = ForecastService(db)
            forecasts = service.generate_forecast(
                product_id=job.product_id,
                model_type=job.model_type,
                horizon=job.horizon,
                user_id=job.requested_by,
            )
            result_payload = {
                "product_id": job.product_id,
                "horizon": job.horizon,
                "model_type": forecasts[0].model_type if forecasts else job.model_type,
                "records_created": len(forecasts),
                "forecasts": [
                    {
                        "period": str(f.period),
                        "predicted_qty": float(f.predicted_qty),
                        "lower_bound": float(f.lower_bound) if f.lower_bound else None,
                        "upper_bound": float(f.upper_bound) if f.upper_bound else None,
                        "confidence": float(f.confidence) if f.confidence else None,
                    }
                    for f in forecasts
                ],
            }

            job.status = "completed"
            job.error = None
            job.result_json = json.dumps(result_payload)
            job.completed_at = datetime.utcnow()
            db.commit()
        except Exception as exc:  # noqa: BLE001
            job = db.query(ForecastJob).filter(ForecastJob.job_id == job_id).first()
            if job:
                job.status = "failed"
                job.error = str(exc)
                job.completed_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()


forecast_job_service = ForecastJobService()
