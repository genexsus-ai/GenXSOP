"""
Integration Tests — Supply Planning Endpoints

Tests:
- GET/POST/PUT/DELETE /api/v1/supply/plans
- Status transitions: draft → submitted → approved
- Gap analysis endpoint
"""
import pytest
from fastapi.testclient import TestClient


class TestSupplyPlanCRUD:

    def test_create_supply_plan(self, client: TestClient, admin_headers, product):
        resp = client.post("/api/v1/supply/plans", headers=admin_headers, json={
            "product_id": product.id,
            "period": "2026-04-01",
            "planned_prod_qty": 480.0,
            "notes": "Initial supply plan",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["product_id"] == product.id
        assert float(data["planned_prod_qty"]) == 480.0
        assert data["status"] == "draft"

    def test_list_supply_plans(self, client: TestClient, admin_headers, supply_plan):
        resp = client.get("/api/v1/supply/plans", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        items = data.get("items", data) if isinstance(data, dict) else data
        assert len(items) >= 1

    def test_get_supply_plan_by_id(self, client: TestClient, admin_headers, supply_plan):
        resp = client.get(f"/api/v1/supply/plans/{supply_plan.id}", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == supply_plan.id

    def test_get_nonexistent_supply_plan_returns_404(self, client: TestClient, admin_headers):
        resp = client.get("/api/v1/supply/plans/99999", headers=admin_headers)
        assert resp.status_code == 404

    def test_update_supply_plan(self, client: TestClient, admin_headers, supply_plan):
        resp = client.put(f"/api/v1/supply/plans/{supply_plan.id}", headers=admin_headers, json={
            "planned_prod_qty": 510.0,
            "notes": "Revised upward",
        })
        assert resp.status_code == 200
        assert float(resp.json()["planned_prod_qty"]) == 510.0

    def test_delete_supply_plan(self, client: TestClient, admin_headers, product):
        create_resp = client.post("/api/v1/supply/plans", headers=admin_headers, json={
            "product_id": product.id,
            "period": "2026-06-01",
            "planned_prod_qty": 200.0,
        })
        plan_id = create_resp.json()["id"]
        del_resp = client.delete(f"/api/v1/supply/plans/{plan_id}", headers=admin_headers)
        assert del_resp.status_code in (200, 204)

    def test_create_supply_plan_unauthenticated_returns_401(self, client: TestClient, product):
        resp = client.post("/api/v1/supply/plans", json={
            "product_id": product.id,
            "period": "2026-04-01",
            "planned_prod_qty": 100.0,
        })
        assert resp.status_code == 401


class TestSupplyPlanStatusTransitions:

    def test_submit_supply_plan(self, client: TestClient, admin_headers, supply_plan):
        resp = client.post(
            f"/api/v1/supply/plans/{supply_plan.id}/submit",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "submitted"

    def test_approve_supply_plan(self, client: TestClient, admin_headers, supply_plan):
        client.post(f"/api/v1/supply/plans/{supply_plan.id}/submit", headers=admin_headers)
        resp = client.post(
            f"/api/v1/supply/plans/{supply_plan.id}/approve",
            headers=admin_headers,
            json={"comment": "Supply plan approved"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"

    def test_reject_supply_plan(self, client: TestClient, admin_headers, supply_plan):
        client.post(f"/api/v1/supply/plans/{supply_plan.id}/submit", headers=admin_headers)
        resp = client.post(
            f"/api/v1/supply/plans/{supply_plan.id}/reject",
            headers=admin_headers,
            json={"comment": "Capacity constraints"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] in ("rejected", "draft")


class TestSupplyGapAnalysis:

    def test_gap_analysis_endpoint(self, client: TestClient, admin_headers, demand_plan, supply_plan):
        resp = client.get(
            f"/api/v1/supply/gap-analysis?product_id={demand_plan.product_id}",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        # Should return gap analysis data
        assert isinstance(data, (list, dict))

    def test_filter_supply_by_product(self, client: TestClient, admin_headers, supply_plan, product):
        resp = client.get(
            f"/api/v1/supply/plans?product_id={product.id}",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        items = data.get("items", data) if isinstance(data, dict) else data
        for item in items:
            assert item["product_id"] == product.id
