"""
Integration Tests — Forecasting Endpoints

Covers:
- POST /api/v1/forecasting/generate diagnostics contract
- Persistence of advisor diagnostics metadata in forecast results
- GET /api/v1/forecasting/accuracy/drift-alerts response contract
"""

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.demand_plan import DemandPlan
from app.models.forecast_consensus import ForecastConsensus
from app.models.forecast_run_audit import ForecastRunAudit


def _seed_actual_history(db: Session, product_id: int, months: int = 18) -> None:
    for idx in range(months):
        month = (idx % 12) + 1
        year = 2024 + (idx // 12)
        db.add(
            DemandPlan(
                product_id=product_id,
                period=date(year, month, 1),
                forecast_qty=Decimal("100.00") + Decimal(idx),
                actual_qty=Decimal("95.00") + Decimal(idx),
                status="approved",
                version=idx + 1,
            )
        )
    db.commit()


class TestForecastingIntegration:
    def test_generate_forecast_returns_diagnostics_contract(
        self,
        client: TestClient,
        admin_headers: dict,
        db: Session,
        product,
    ):
        _seed_actual_history(db, product.id, months=18)

        resp = client.post(
            "/api/v1/forecasting/generate",
            params={"product_id": product.id, "horizon": 6},
            headers=admin_headers,
        )

        assert resp.status_code == 200
        data = resp.json()

        assert data["product_id"] == product.id
        assert isinstance(data.get("forecasts"), list)
        assert len(data["forecasts"]) > 0

        diagnostics = data.get("diagnostics")
        assert isinstance(diagnostics, dict)
        for key in [
            "selected_model",
            "selection_reason",
            "advisor_confidence",
            "advisor_enabled",
            "fallback_used",
            "warnings",
            "history_months",
            "candidate_metrics",
            "data_quality_flags",
        ]:
            assert key in diagnostics

    def test_generate_persists_advisor_metadata_in_results(
        self,
        client: TestClient,
        admin_headers: dict,
        db: Session,
        product,
    ):
        _seed_actual_history(db, product.id, months=18)

        gen = client.post(
            "/api/v1/forecasting/generate",
            params={"product_id": product.id, "horizon": 3},
            headers=admin_headers,
        )
        assert gen.status_code == 200

        results = client.get(
            "/api/v1/forecasting/results",
            params={"product_id": product.id},
            headers=admin_headers,
        )
        assert results.status_code == 200
        payload = results.json()
        assert isinstance(payload, list)
        assert len(payload) > 0

        row = payload[0]
        assert row.get("selection_reason") is not None
        assert "advisor_confidence" in row
        assert "advisor_enabled" in row
        assert "fallback_used" in row
        assert "warnings" in row

        audit = (
            db.query(ForecastRunAudit)
            .filter(ForecastRunAudit.product_id == product.id)
            .order_by(ForecastRunAudit.created_at.desc())
            .first()
        )
        assert audit is not None
        assert audit.selected_model is not None
        assert audit.history_months >= 3
        assert audit.records_created > 0

    def test_drift_alerts_endpoint_contract(
        self,
        client: TestClient,
        admin_headers: dict,
        db: Session,
        product,
    ):
        _seed_actual_history(db, product.id, months=18)

        # Generate forecasts a couple times to populate records used in drift checks
        client.post(
            "/api/v1/forecasting/generate",
            params={"product_id": product.id, "horizon": 6, "model_type": "moving_average"},
            headers=admin_headers,
        )
        client.post(
            "/api/v1/forecasting/generate",
            params={"product_id": product.id, "horizon": 6, "model_type": "exp_smoothing"},
            headers=admin_headers,
        )

        resp = client.get(
            "/api/v1/forecasting/accuracy/drift-alerts",
            params={"threshold_pct": 0, "min_points": 3},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            sample = data[0]
            for key in [
                "product_id",
                "model_type",
                "previous_mape",
                "recent_mape",
                "degradation_pct",
                "severity",
            ]:
                assert key in sample

    def test_consensus_create_update_and_list(
        self,
        client: TestClient,
        admin_headers: dict,
        product,
    ):
        created = client.post(
            "/api/v1/forecasting/consensus",
            json={
                "product_id": product.id,
                "period": "2026-07-01",
                "baseline_qty": "1000.00",
                "sales_override_qty": "50.00",
                "marketing_uplift_qty": "120.00",
                "finance_adjustment_qty": "-40.00",
                "constraint_cap_qty": "1080.00",
                "notes": "Initial consensus draft",
            },
            headers=admin_headers,
        )
        assert created.status_code == 201
        row = created.json()
        assert row["product_id"] == product.id
        assert row["pre_consensus_qty"] == "1130.00"
        assert row["final_consensus_qty"] == "1080.00"
        assert row["status"] == "draft"

        updated = client.patch(
            f"/api/v1/forecasting/consensus/{row['id']}",
            json={"constraint_cap_qty": None, "status": "proposed"},
            headers=admin_headers,
        )
        assert updated.status_code == 200
        upd = updated.json()
        assert upd["status"] == "proposed"
        assert upd["constraint_cap_qty"] is None
        assert upd["final_consensus_qty"] == "1130.00"
        assert upd["version"] == row["version"] + 1

        listed = client.get(
            "/api/v1/forecasting/consensus",
            params={"product_id": product.id},
            headers=admin_headers,
        )
        assert listed.status_code == 200
        payload = listed.json()
        assert isinstance(payload, list)
        assert len(payload) >= 1

    def test_consensus_approval_syncs_demand_plan(
        self,
        client: TestClient,
        admin_headers: dict,
        db: Session,
        product,
    ):
        create_resp = client.post(
            "/api/v1/forecasting/consensus",
            json={
                "product_id": product.id,
                "period": "2026-08-01",
                "baseline_qty": "500.00",
                "sales_override_qty": "25.00",
                "marketing_uplift_qty": "10.00",
                "finance_adjustment_qty": "-5.00",
            },
            headers=admin_headers,
        )
        assert create_resp.status_code == 201
        consensus_id = create_resp.json()["id"]

        approve_resp = client.post(
            f"/api/v1/forecasting/consensus/{consensus_id}/approve",
            json={"notes": "Approved in demand review"},
            headers=admin_headers,
        )
        assert approve_resp.status_code == 200
        approved = approve_resp.json()
        assert approved["status"] == "approved"
        assert approved["approved_by"] is not None
        assert approved["final_consensus_qty"] == "530.00"

        demand_plan = (
            db.query(DemandPlan)
            .filter(
                DemandPlan.product_id == product.id,
                DemandPlan.period == date(2026, 8, 1),
            )
            .first()
        )
        assert demand_plan is not None
        assert str(demand_plan.consensus_qty) == "530.00"

        consensus = db.query(ForecastConsensus).filter(ForecastConsensus.id == consensus_id).first()
        assert consensus is not None
        assert consensus.status == "approved"
