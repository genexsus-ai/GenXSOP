"""
Forecast Service — Service Layer (SRP / DIP)
Uses Strategy + Factory patterns for ML model selection.
"""
from typing import Optional, List, Dict, Any
from datetime import date
from math import sqrt
import json
from decimal import Decimal
import pandas as pd
from sqlalchemy.orm import Session

from app.repositories.forecast_repository import ForecastRepository
from app.repositories.forecast_consensus_repository import ForecastConsensusRepository
from app.repositories.demand_repository import DemandPlanRepository
from app.models.forecast import Forecast
from app.models.demand_plan import DemandPlan
from app.models.forecast_run_audit import ForecastRunAudit
from app.ml.factory import ForecastModelFactory
from app.ml.anomaly_detection import AnomalyDetector
from app.services.forecast_advisor_service import ForecastAdvisorService
from app.core.exceptions import EntityNotFoundException, InsufficientDataException, to_http_exception
from app.utils.events import get_event_bus, ForecastGeneratedEvent


class ForecastService:

    def __init__(self, db: Session):
        self._db = db
        self._repo = ForecastRepository(db)
        self._consensus_repo = ForecastConsensusRepository(db)
        self._demand_repo = DemandPlanRepository(db)
        self._bus = get_event_bus()
        self._advisor = ForecastAdvisorService()

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

    def delete_forecast(self, forecast_id: int) -> None:
        forecast = self._repo.get_by_id(forecast_id)
        if not forecast:
            raise to_http_exception(EntityNotFoundException("Forecast", forecast_id))
        self._repo.delete(forecast)

    def delete_forecasts_by_product(self, product_id: int) -> Dict[str, int]:
        """
        Delete forecast outputs and dependent consensus rows for the same product.
        Kept transactional to avoid partial deletion state.
        """
        forecasts_deleted = self._repo.delete_by_product(product_id, commit=False)
        consensus_deleted = self._consensus_repo.delete_by_product(product_id, commit=False)
        self._db.commit()
        return {
            "forecasts_deleted": forecasts_deleted,
            "consensus_deleted": consensus_deleted,
        }

    def generate_forecast(
        self,
        product_id: int,
        model_type: Optional[str],
        horizon: int,
        user_id: int,
    ) -> List[Forecast]:
        """Compatibility method returning only saved forecast records."""
        return self.generate_forecast_with_diagnostics(
            product_id=product_id,
            model_type=model_type,
            horizon=horizon,
            user_id=user_id,
        )["forecasts"]

    def generate_forecast_with_diagnostics(
        self,
        product_id: int,
        model_type: Optional[str],
        horizon: int,
        user_id: int,
    ) -> Dict[str, Any]:
        """
        Generate forecast with model diagnostics and advisor metadata.
        """
        advisor_payload = self.recommend_model(product_id=product_id, model_type=model_type)
        advisor = advisor_payload["advisor"]

        context = ForecastModelFactory.create_context(advisor.recommended_model)
        history_df = advisor_payload["history_df"]

        run_audit = ForecastRunAudit(
            product_id=product_id,
            user_id=user_id,
            requested_model=model_type,
            selected_model=context.strategy.model_id,
            horizon=horizon,
            advisor_enabled=advisor.advisor_enabled,
            fallback_used=advisor.fallback_used,
            advisor_confidence=advisor.confidence,
            selection_reason=advisor.reason,
            history_months=advisor_payload["history_months"],
            records_created=0,
            warnings_json=json.dumps(advisor.warnings),
            candidate_metrics_json=json.dumps(advisor_payload["candidate_metrics"]),
            data_quality_flags_json=json.dumps(advisor_payload["data_quality_flags"]),
        )
        self._db.add(run_audit)
        self._db.flush()

        predictions = context.execute(history_df, horizon)
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
                model_version="genxai-advisor-v1",
                features_used=json.dumps({
                    "run_audit_id": run_audit.id,
                    "selection_reason": advisor.reason,
                    "advisor_confidence": advisor.confidence,
                    "advisor_enabled": advisor.advisor_enabled,
                    "fallback_used": advisor.fallback_used,
                    "warnings": advisor.warnings,
                }),
            )
            created.append(self._repo.create(forecast))

        diagnostics = {
            "selected_model": context.strategy.model_id,
            "selection_reason": advisor.reason,
            "advisor_confidence": advisor.confidence,
            "advisor_enabled": advisor.advisor_enabled,
            "fallback_used": advisor.fallback_used,
            "warnings": advisor.warnings,
            "history_months": advisor_payload["history_months"],
            "candidate_metrics": advisor_payload["candidate_metrics"],
            "data_quality_flags": advisor_payload["data_quality_flags"],
            "run_audit_id": run_audit.id,
        }

        run_audit.records_created = len(created)
        self._db.commit()

        self._bus.publish(ForecastGeneratedEvent(
            product_id=product_id,
            model_type=context.strategy.model_id,
            horizon_months=horizon,
            records_created=len(created),
            user_id=user_id,
        ))
        return {
            "forecasts": created,
            "diagnostics": diagnostics,
        }

    def recommend_model(self, product_id: int, model_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Return advisor recommendation diagnostics without generating forecast records.
        """
        history = self._demand_repo.get_with_actuals(product_id)
        if len(history) < 3:
            raise to_http_exception(
                InsufficientDataException(required=3, available=len(history), operation="forecast recommendation")
            )

        df = pd.DataFrame([
            {"ds": pd.Timestamp(h.period), "y": float(h.actual_qty)}
            for h in history
        ])

        candidate_metrics = self._run_backtests(df)
        default_model = self._select_default_model(len(history), candidate_metrics)
        data_quality_flags = self._data_quality_flags(df)
        advisor = self._advisor.recommend_model(
            requested_model=model_type,
            default_model=default_model,
            candidate_metrics=candidate_metrics,
            history_months=len(history),
            data_quality_flags=data_quality_flags,
        )

        diagnostics = {
            "selected_model": advisor.recommended_model,
            "selection_reason": advisor.reason,
            "advisor_confidence": advisor.confidence,
            "advisor_enabled": advisor.advisor_enabled,
            "fallback_used": advisor.fallback_used,
            "warnings": advisor.warnings,
            "history_months": len(history),
            "candidate_metrics": candidate_metrics,
            "data_quality_flags": data_quality_flags,
        }

        return {
            "diagnostics": diagnostics,
            "advisor": advisor,
            "history_df": df,
            "history_months": len(history),
            "candidate_metrics": candidate_metrics,
            "data_quality_flags": data_quality_flags,
        }

    def get_model_comparison(
        self,
        product_id: int,
        test_months: int = 6,
        min_train_months: int = 6,
        models: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Compare model performance using walk-forward backtesting on historical actuals.
        """
        history = self._demand_repo.get_with_actuals(product_id)
        if len(history) < 3:
            raise to_http_exception(
                InsufficientDataException(required=3, available=len(history), operation="model comparison")
            )

        df = pd.DataFrame([
            {"ds": pd.Timestamp(h.period), "y": float(h.actual_qty)}
            for h in history
        ])

        comparison_rows = self._run_backtests(
            df=df,
            test_months=test_months,
            min_train_months=min_train_months,
            models=models,
            include_series=True,
        )

        ranked_rows = [
            {**row, "rank": idx + 1}
            for idx, row in enumerate(comparison_rows)
        ]
        return {
            "product_id": product_id,
            "history_months": len(history),
            "test_months": test_months,
            "min_train_months": min_train_months,
            "models": ranked_rows,
            "data_quality_flags": self._data_quality_flags(df),
        }

    def promote_forecast_results_to_demand_plan(
        self,
        product_id: int,
        selected_model: str,
        horizon: int,
        user_id: int,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Persist selected forecast model output into demand planning records.
        """
        forecasts = self._repo.list_filtered(product_id=product_id, model_type=selected_model)
        if not forecasts:
            raise to_http_exception(EntityNotFoundException("ForecastResults", f"{product_id}:{selected_model}"))

        selected_forecasts = sorted(forecasts, key=lambda f: f.period)
        if horizon > 0:
            selected_forecasts = selected_forecasts[:horizon]

        promoted = []
        for row in selected_forecasts:
            period = row.period
            existing = self._demand_repo.get_by_product_and_period(product_id=product_id, period=period)
            qty = Decimal(str(row.predicted_qty))
            note_suffix = f"[ForecastPromotion] model={selected_model}"
            if notes:
                note_suffix = f"{note_suffix}; user_note={notes}"

            if existing:
                updated = self._demand_repo.update(existing, {
                    "forecast_qty": qty,
                    "consensus_qty": qty,
                    "confidence": Decimal(str(row.confidence or 0)),
                    "notes": f"{(existing.notes or '').strip()}\n{note_suffix}".strip(),
                    "version": existing.version + 1,
                })
                promoted.append(updated)
            else:
                new_plan = DemandPlan(
                    product_id=product_id,
                    period=period,
                    region="Global",
                    channel="All",
                    forecast_qty=qty,
                    consensus_qty=qty,
                    confidence=Decimal(str(row.confidence or 0)),
                    notes=note_suffix,
                    status="draft",
                    created_by=user_id,
                    version=1,
                )
                promoted.append(self._demand_repo.create(new_plan))

        return {
            "product_id": product_id,
            "selected_model": selected_model,
            "records_promoted": len(promoted),
            "periods": [str(p.period) for p in promoted],
        }

    def get_accuracy_metrics(self, product_id: Optional[int] = None) -> List[dict]:
        """Return richer accuracy metrics per model."""
        model_ids = [m["id"] for m in ForecastModelFactory.list_models()]
        rows: List[dict] = []

        if product_id:
            plans = self._demand_repo.get_all_for_product(product_id)
            plans_by_period = {
                str(p.period): float(p.actual_qty)
                for p in plans
                if p.actual_qty is not None
            }
            for model_id in model_ids:
                forecasts = self._repo.list_filtered(product_id=product_id, model_type=model_id)
                metrics = self._compute_error_metrics_from_forecasts(forecasts, plans_by_period)
                if metrics:
                    rows.append({"product_id": product_id, "model_type": model_id, **metrics})
            return rows

        # Aggregate over all products by model
        products = {f.product_id for f in self._repo.list_filtered()}
        by_model: Dict[str, List[dict]] = {m: [] for m in model_ids}
        for pid in products:
            plans = self._demand_repo.get_all_for_product(pid)
            plans_by_period = {
                str(p.period): float(p.actual_qty)
                for p in plans
                if p.actual_qty is not None
            }
            for model_id in model_ids:
                forecasts = self._repo.list_filtered(product_id=pid, model_type=model_id)
                metrics = self._compute_error_metrics_from_forecasts(forecasts, plans_by_period)
                if metrics:
                    by_model[model_id].append(metrics)

        for model_id, samples in by_model.items():
            if not samples:
                continue
            rows.append({
                "product_id": 0,
                "model_type": model_id,
                "mape": round(sum(s["mape"] for s in samples) / len(samples), 4),
                "wape": round(sum(s["wape"] for s in samples) / len(samples), 4),
                "rmse": round(sum(s["rmse"] for s in samples) / len(samples), 4),
                "mae": round(sum(s["mae"] for s in samples) / len(samples), 4),
                "bias": round(sum(s["bias"] for s in samples) / len(samples), 4),
                "hit_rate": round(sum(s["hit_rate"] for s in samples) / len(samples), 4),
                "period_count": int(sum(s["period_count"] for s in samples)),
                "sample_count": int(sum(s["period_count"] for s in samples)),
                "avg_mape": round(sum(s["mape"] for s in samples) / len(samples), 4),
            })
        return rows

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

    def get_accuracy_drift_alerts(self, threshold_pct: float = 10.0, min_points: int = 6) -> List[dict]:
        """Detect month-over-month degradation by comparing recent vs prior error windows."""
        alerts: List[dict] = []
        model_ids = [m["id"] for m in ForecastModelFactory.list_models()]
        product_ids = {f.product_id for f in self._repo.list_filtered()}

        for product_id in product_ids:
            plans = self._demand_repo.get_all_for_product(product_id)
            actuals = {str(p.period): float(p.actual_qty) for p in plans if p.actual_qty is not None}

            for model_id in model_ids:
                forecasts = self._repo.list_filtered(product_id=product_id, model_type=model_id)
                series: List[float] = []
                for f in forecasts:
                    actual = actuals.get(str(f.period))
                    if actual is None or actual == 0:
                        continue
                    ape = abs((float(f.predicted_qty) - actual) / actual) * 100.0
                    series.append(ape)

                if len(series) < min_points:
                    continue

                window = max(3, min(6, len(series) // 2))
                if len(series) < window * 2:
                    continue

                previous_avg = sum(series[-2 * window:-window]) / window
                recent_avg = sum(series[-window:]) / window
                degradation = recent_avg - previous_avg

                if degradation >= threshold_pct:
                    alerts.append({
                        "product_id": product_id,
                        "model_type": model_id,
                        "previous_mape": round(previous_avg, 4),
                        "recent_mape": round(recent_avg, 4),
                        "degradation_pct": round(degradation, 4),
                        "severity": "high" if degradation >= threshold_pct * 2 else "medium",
                    })

        return sorted(alerts, key=lambda a: a["degradation_pct"], reverse=True)

    def _run_backtests(
        self,
        df: pd.DataFrame,
        test_months: int = 6,
        min_train_months: int = 3,
        models: Optional[List[str]] = None,
        include_series: bool = False,
    ) -> List[dict]:
        metrics: List[dict] = []
        available_model_ids = [m["id"] for m in ForecastModelFactory.list_models()]
        model_ids = [m for m in (models or available_model_ids) if m in available_model_ids]
        n = len(df)

        for model_id in model_ids:
            # Backtesting should benchmark *all* registered models, not only those
            # whose strict minimum history threshold is met. Each strategy already
            # has guarded fallback behavior (e.g., ARIMA -> exp smoothing -> moving
            # average), so we can safely evaluate every model with a shared minimum
            # training window.
            min_history = max(3, min_train_months)
            if n <= min_history:
                continue

            start = max(min_history, n - max(1, test_months))
            abs_errors: List[float] = []
            sq_errors: List[float] = []
            pct_errors: List[float] = []
            bias_pct: List[float] = []
            hits = 0
            samples = 0
            actual_sum = 0.0
            series_points: List[dict] = []

            for split in range(start, n):
                train = df.iloc[:split]
                actual = float(df.iloc[split]["y"])
                pred = float(ForecastModelFactory.create_context(model_id).execute(train, 1)[0]["predicted_qty"])
                err = pred - actual
                abs_err = abs(err)
                abs_errors.append(abs_err)
                sq_errors.append(err ** 2)
                if include_series:
                    period = pd.Timestamp(df.iloc[split]["ds"]).date()
                    series_points.append({
                        "period": str(period),
                        "actual_qty": round(actual, 4),
                        "predicted_qty": round(pred, 4),
                    })
                actual_sum += abs(actual)
                if actual != 0:
                    pct = abs_err / abs(actual)
                    pct_errors.append(pct)
                    bias_pct.append(err / actual)
                    if pct <= 0.2:
                        hits += 1
                samples += 1

            if samples == 0:
                continue

            mape = (sum(pct_errors) / len(pct_errors) * 100.0) if pct_errors else 0.0
            wape = (sum(abs_errors) / actual_sum * 100.0) if actual_sum > 0 else 0.0
            rmse = sqrt(sum(sq_errors) / len(sq_errors))
            mae = sum(abs_errors) / len(abs_errors)
            bias = (sum(bias_pct) / len(bias_pct) * 100.0) if bias_pct else 0.0
            hit_rate = (hits / len(pct_errors) * 100.0) if pct_errors else 0.0

            metrics.append({
                "model_type": model_id,
                "mape": round(mape, 4),
                "wape": round(wape, 4),
                "rmse": round(rmse, 4),
                "mae": round(mae, 4),
                "bias": round(bias, 4),
                "hit_rate": round(hit_rate, 4),
                "period_count": samples,
                "score": round(mape + (wape * 0.25), 4),
                **({"series": series_points} if include_series else {}),
            })

        return sorted(metrics, key=lambda m: m["score"])

    def _select_default_model(self, history_months: int, candidate_metrics: List[dict]) -> str:
        if candidate_metrics:
            return candidate_metrics[0]["model_type"]
        return ForecastModelFactory.get_best_strategy(history_months).model_id

    def _data_quality_flags(self, df: pd.DataFrame) -> List[str]:
        flags: List[str] = []
        if len(df) < 12:
            flags.append("short_history")
        if len(df) > 1:
            expected = pd.date_range(df["ds"].min(), df["ds"].max(), freq="MS")
            if len(expected) != len(df["ds"].drop_duplicates()):
                flags.append("missing_months")
        if len(df) > 3 and float(df["y"].std()) > (float(df["y"].mean()) * 1.5):
            flags.append("high_volatility")
        return flags

    def _compute_error_metrics_from_forecasts(self, forecasts: List[Forecast], actual_by_period: Dict[str, float]) -> Optional[dict]:
        abs_errors: List[float] = []
        sq_errors: List[float] = []
        pct_errors: List[float] = []
        bias_pct: List[float] = []
        hits = 0
        actual_sum = 0.0

        for f in forecasts:
            actual = actual_by_period.get(str(f.period))
            if actual is None:
                continue
            pred = float(f.predicted_qty)
            err = pred - actual
            abs_err = abs(err)
            abs_errors.append(abs_err)
            sq_errors.append(err ** 2)
            actual_sum += abs(actual)
            if actual != 0:
                pct = abs_err / abs(actual)
                pct_errors.append(pct)
                bias_pct.append(err / actual)
                if pct <= 0.2:
                    hits += 1

        if not abs_errors:
            return None

        mape = (sum(pct_errors) / len(pct_errors) * 100.0) if pct_errors else 0.0
        wape = (sum(abs_errors) / actual_sum * 100.0) if actual_sum > 0 else 0.0
        rmse = sqrt(sum(sq_errors) / len(sq_errors))
        mae = sum(abs_errors) / len(abs_errors)
        bias = (sum(bias_pct) / len(bias_pct) * 100.0) if bias_pct else 0.0
        hit_rate = (hits / len(pct_errors) * 100.0) if pct_errors else 0.0
        period_count = len(abs_errors)

        return {
            "mape": round(mape, 4),
            "wape": round(wape, 4),
            "rmse": round(rmse, 4),
            "mae": round(mae, 4),
            "bias": round(bias, 4),
            "hit_rate": round(hit_rate, 4),
            "period_count": period_count,
            "sample_count": period_count,
            "avg_mape": round(mape, 4),
        }
