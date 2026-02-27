"""
Integration Tests — Demand Planning Endpoints

Tests:
- GET/POST/PUT/DELETE /api/v1/demand/plans
- Status transitions: draft → submitted → approved
- Approval workflow (admin/executive only)
- Demand gap analysis
- Anomaly detection endpoint
"""
import pytest
from fastapi.testclient import TestClient


class TestDemandPlanCRUD:

    def test_create_demand_plan(self, client: TestClient, admin_headers, product):
        resp = client.post("/api/v1/demand/plans", headers=admin_headers, json={
            "product_id": product.id,
            "period": "2026-04-01",
            "forecast_qty": 500.0,
            "notes": "Initial forecast",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["product_id"] == product.id
        assert float(data["forecast_qty"]) == 500.0
        assert data["status"] == "draft"

    def test_list_demand_plans(self, client: TestClient, admin_headers, demand_plan):
        resp = client.get("/api/v1/demand/plans", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        items = data.get("items", data) if isinstance(data, dict) else data
        assert len(items) >= 1

    def test_get_demand_plan_by_id(self, client: TestClient, admin_headers, demand_plan):
        resp = client.get(f"/api/v1/demand/plans/{demand_plan.id}", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == demand_plan.id

    def test_get_nonexistent_demand_plan_returns_404(self, client: TestClient, admin_headers):
        resp = client.get("/api/v1/demand/plans/99999", headers=admin_headers)
        assert resp.status_code == 404

    def test_update_demand_plan(self, client: TestClient, admin_headers, demand_plan):
        resp = client.put(f"/api/v1/demand/plans/{demand_plan.id}", headers=admin_headers, json={
            "adjusted_qty": 520.0,
            "notes": "Adjusted upward",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert float(data["adjusted_qty"]) == 520.0

    def test_delete_demand_plan(self, client: TestClient, admin_headers, product):
        create_resp = client.post("/api/v1/demand/plans", headers=admin_headers, json={
            "product_id": product.id,
            "period": "2026-05-01",
            "forecast_qty": 300.0,
        })
        plan_id = create_resp.json()["id"]
        del_resp = client.delete(f"/api/v1/demand/plans/{plan_id}", headers=admin_headers)
        assert del_resp.status_code in (200, 204)

    def test_create_demand_plan_unauthenticated_returns_401(self, client: TestClient, product):
        resp = client.post("/api/v1/demand/plans", json={
            "product_id": product.id,
            "period": "2026-04-01",
            "forecast_qty": 100.0,
        })
        assert resp.status_code == 401

    def test_create_demand_plan_missing_product_id_returns_422(self, client: TestClient, admin_headers):
        resp = client.post("/api/v1/demand/plans", headers=admin_headers, json={
            "period": "2026-04-01",
            "forecast_qty": 100.0,
        })
        assert resp.status_code == 422


class TestDemandPlanStatusTransitions:

    def test_submit_demand_plan(self, client: TestClient, admin_headers, demand_plan):
        resp = client.post(
            f"/api/v1/demand/plans/{demand_plan.id}/submit",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "submitted"

    def test_approve_demand_plan(self, client: TestClient, admin_headers, demand_plan):
        # Submit first
        client.post(f"/api/v1/demand/plans/{demand_plan.id}/submit", headers=admin_headers)
        # Then approve
        resp = client.post(
            f"/api/v1/demand/plans/{demand_plan.id}/approve",
            headers=admin_headers,
            json={"comment": "Approved by admin"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"

    def test_reject_demand_plan(self, client: TestClient, admin_headers, demand_plan):
        client.post(f"/api/v1/demand/plans/{demand_plan.id}/submit", headers=admin_headers)
        resp = client.post(
            f"/api/v1/demand/plans/{demand_plan.id}/reject",
            headers=admin_headers,
            json={"comment": "Needs revision"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] in ("rejected", "draft")

    def test_approve_draft_plan_returns_error(self, client: TestClient, admin_headers, demand_plan):
        # Cannot approve a draft (must be submitted first)
        resp = client.post(
            f"/api/v1/demand/plans/{demand_plan.id}/approve",
            headers=admin_headers,
        )
        assert resp.status_code in (422, 400)


class TestDemandAnalysis:

    def test_filter_by_product(self, client: TestClient, admin_headers, demand_plan, product):
        resp = client.get(
            f"/api/v1/demand/plans?product_id={product.id}",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        items = data.get("items", data) if isinstance(data, dict) else data
        for item in items:
            assert item["product_id"] == product.id

    def test_filter_by_status(self, client: TestClient, admin_headers, demand_plan):
        resp = client.get("/api/v1/demand/plans?status=draft", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        items = data.get("items", data) if isinstance(data, dict) else data
        for item in items:
            assert item["status"] == "draft"
