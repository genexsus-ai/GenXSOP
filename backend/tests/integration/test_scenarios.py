"""
Integration Tests — Scenario Planning Endpoints

Tests:
- GET/POST/PUT/DELETE /api/v1/scenarios
- Scenario comparison
- Scenario approval workflow
"""
import pytest
from fastapi.testclient import TestClient


class TestScenarioCRUD:

    def test_create_scenario(self, client: TestClient, admin_headers):
        resp = client.post("/api/v1/scenarios/", headers=admin_headers, json={
            "name": "Optimistic Q2 2026",
            "description": "Best-case demand scenario",
            "scenario_type": "optimistic",
            "assumptions": {"demand_growth": 0.15, "supply_capacity": 1.0},
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Optimistic Q2 2026"
        assert data["status"] == "draft"
        assert "id" in data

    def test_list_scenarios(self, client: TestClient, admin_headers):
        # Create one first
        client.post("/api/v1/scenarios/", headers=admin_headers, json={
            "name": "Base Case",
            "scenario_type": "base",
        })
        resp = client.get("/api/v1/scenarios/", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        items = data.get("items", data) if isinstance(data, dict) else data
        assert len(items) >= 1

    def test_get_scenario_by_id(self, client: TestClient, admin_headers):
        create_resp = client.post("/api/v1/scenarios/", headers=admin_headers, json={
            "name": "Test Scenario",
            "scenario_type": "pessimistic",
        })
        scenario_id = create_resp.json()["id"]
        resp = client.get(f"/api/v1/scenarios/{scenario_id}", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == scenario_id

    def test_get_nonexistent_scenario_returns_404(self, client: TestClient, admin_headers):
        resp = client.get("/api/v1/scenarios/99999", headers=admin_headers)
        assert resp.status_code == 404

    def test_update_scenario(self, client: TestClient, admin_headers):
        create_resp = client.post("/api/v1/scenarios/", headers=admin_headers, json={
            "name": "Original Name",
            "scenario_type": "base",
        })
        scenario_id = create_resp.json()["id"]
        resp = client.put(f"/api/v1/scenarios/{scenario_id}", headers=admin_headers, json={
            "name": "Updated Name",
            "description": "Updated description",
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"

    def test_delete_scenario(self, client: TestClient, admin_headers):
        create_resp = client.post("/api/v1/scenarios/", headers=admin_headers, json={
            "name": "To Delete",
            "scenario_type": "base",
        })
        scenario_id = create_resp.json()["id"]
        del_resp = client.delete(f"/api/v1/scenarios/{scenario_id}", headers=admin_headers)
        assert del_resp.status_code in (200, 204)

    def test_create_scenario_unauthenticated_returns_401(self, client: TestClient):
        resp = client.post("/api/v1/scenarios/", json={"name": "Hack", "scenario_type": "base"})
        assert resp.status_code == 401


class TestScenarioWorkflow:

    def test_submit_scenario(self, client: TestClient, admin_headers):
        create_resp = client.post("/api/v1/scenarios/", headers=admin_headers, json={
            "name": "Submit Test",
            "scenario_type": "optimistic",
        })
        scenario_id = create_resp.json()["id"]
        resp = client.post(f"/api/v1/scenarios/{scenario_id}/submit", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "submitted"

    def test_approve_scenario(self, client: TestClient, admin_headers):
        create_resp = client.post("/api/v1/scenarios/", headers=admin_headers, json={
            "name": "Approve Test",
            "scenario_type": "base",
        })
        scenario_id = create_resp.json()["id"]
        client.post(f"/api/v1/scenarios/{scenario_id}/submit", headers=admin_headers)
        resp = client.post(
            f"/api/v1/scenarios/{scenario_id}/approve",
            headers=admin_headers,
            json={"comment": "Approved for planning"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"


class TestScenarioComparison:

    def test_compare_scenarios(self, client: TestClient, admin_headers):
        # Create two scenarios
        s1 = client.post("/api/v1/scenarios/", headers=admin_headers, json={
            "name": "Scenario A", "scenario_type": "optimistic",
        }).json()["id"]
        s2 = client.post("/api/v1/scenarios/", headers=admin_headers, json={
            "name": "Scenario B", "scenario_type": "pessimistic",
        }).json()["id"]

        resp = client.get(
            f"/api/v1/scenarios/compare?ids={s1}&ids={s2}",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, (list, dict))
