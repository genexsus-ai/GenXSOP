"""
Forecast Job Maintenance Utility

Provides a lightweight runner-style helper to execute retention cleanup
outside request/response flow (e.g., cron, CI, scheduled task runner).
"""

from __future__ import annotations

from typing import Optional

from app.services.forecast_job_service import forecast_job_service


def run_forecast_job_cleanup(retention_days: Optional[int] = None, requested_by: Optional[int] = None) -> dict:
    """Execute cleanup and return structured summary."""
    return forecast_job_service.cleanup_old_jobs(
        retention_days=retention_days,
        requested_by=requested_by,
    )
