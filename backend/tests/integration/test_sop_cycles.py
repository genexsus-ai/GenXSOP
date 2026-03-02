"""
Integration Tests — S&OP Cycle Endpoints

Tests:
- GET/POST /api/v1/sop-cycles
- 5-step cycle advancement
- Cycle completion
- Step validation
"""
import pytest
from fastapi.testclient import TestClient


class TestSOPCycleCRUD:

    def test_create_sop_cycle(self, client: TestClient, admin_headers):
        resp = client.post("/api/v1/sop-cycles/", headers=admin_headers, json={
            "cycle_name": "March 2026 S&OP",
            "period": "2026-03-01",
            "notes": "Monthly S&OP cycle",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["cycle_name"] == "March 2026 S&OP"
        assert data["current_step"] == 1
        assert data["overall_status"] == "active"
        assert "id" in data

    def test_list_sop_cycles(self, client: TestClient, admin_headers):
        client.post("/api/v1/sop-cycles/", headers=admin_headers, json={
            "cycle_name": "April 2026 S&OP",
            "period": "2026-04-01",
        })
        resp = client.get("/api/v1/sop-cycles/", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        items = data.get("items", data) if isinstance(data, dict) else data
        assert len(items) >= 1

    def test_get_sop_cycle_by_id(self, client: TestClient, admin_headers):
        create_resp = client.post("/api/v1/sop-cycles/", headers=admin_headers, json={
            "cycle_name": "Test Cycle",
            "period": "2026-05-01",
        })
        cycle_id = create_resp.json()["id"]
        resp = client.get(f"/api/v1/sop-cycles/{cycle_id}", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == cycle_id

    def test_get_nonexistent_cycle_returns_404(self, client: TestClient, admin_headers):
        resp = client.get("/api/v1/sop-cycles/99999", headers=admin_headers)
        assert resp.status_code == 404

    def test_create_sop_cycle_unauthenticated_returns_403(self, client: TestClient):
        resp = client.post("/api/v1/sop-cycles/", json={
            "cycle_name": "Hack Cycle",
            "period": "2026-03-01",
        })
        assert resp.status_code == 403


class TestSOPCycleStepAdvancement:

    def _create_cycle(self, client, headers):
        resp = client.post("/api/v1/sop-cycles/", headers=headers, json={
            "cycle_name": "Step Test Cycle",
            "period": "2026-06-01",
        })
        return resp.json()["id"]

    def test_advance_from_step_1_to_2(self, client: TestClient, admin_headers):
        cycle_id = self._create_cycle(client, admin_headers)
        resp = client.post(
            f"/api/v1/sop-cycles/{cycle_id}/advance",
            headers=admin_headers,
            json={"notes": "Data gathering complete"},
        )
        assert resp.status_code == 200
        assert resp.json()["current_step"] == 2

    def test_advance_through_all_steps(self, client: TestClient, admin_headers):
        cycle_id = self._create_cycle(client, admin_headers)
        for step in range(1, 5):
            resp = client.post(
                f"/api/v1/sop-cycles/{cycle_id}/advance",
                headers=admin_headers,
                json={"notes": f"Step {step} complete"},
            )
            assert resp.status_code == 200
            assert resp.json()["current_step"] == step + 1

    def test_complete_cycle_at_step_5(self, client: TestClient, admin_headers):
        cycle_id = self._create_cycle(client, admin_headers)
        # Advance through steps 1-4
        for _ in range(4):
            client.post(f"/api/v1/sop-cycles/{cycle_id}/advance", headers=admin_headers)
        # Complete at step 5
        resp = client.post(
            f"/api/v1/sop-cycles/{cycle_id}/complete",
            headers=admin_headers,
            json={"notes": "Executive S&OP complete"},
        )
        assert resp.status_code == 200
        assert resp.json()["overall_status"] == "completed"


class TestSOPCycleFilters:

    def test_filter_by_status(self, client: TestClient, admin_headers):
        client.post("/api/v1/sop-cycles/", headers=admin_headers, json={
            "cycle_name": "Active Cycle",
            "period": "2026-07-01",
        })
        resp = client.get("/api/v1/sop-cycles/", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        items = data.get("items", data) if isinstance(data, dict) else data
        for item in items:
            assert item["overall_status"] in ["active", "completed", "cancelled"]


class TestSOPCycleExecutiveScorecard:

    def test_get_executive_scorecard(self, client: TestClient, admin_headers, demand_plan, supply_plan, inventory):
        cycle_resp = client.post(
            "/api/v1/sop-cycles/",
            headers=admin_headers,
            json={
                "cycle_name": "March 2026 Exec Board",
                "period": "2026-03-01",
            },
        )
        assert cycle_resp.status_code == 201
        cycle_id = cycle_resp.json()["id"]

        scen_resp = client.post(
            "/api/v1/scenarios/",
            headers=admin_headers,
            json={
                "name": "Cycle-linked Scenario",
                "scenario_type": "what_if",
                "parameters": {
                    "period": "2026-03-01",
                    "demand_change_pct": 7,
                    "supply_capacity_pct": -2,
                },
            },
        )
        assert scen_resp.status_code == 201
        scenario_id = scen_resp.json()["id"]
        run_resp = client.post(f"/api/v1/scenarios/{scenario_id}/run", headers=admin_headers)
        assert run_resp.status_code == 200

        score_resp = client.get(f"/api/v1/sop-cycles/{cycle_id}/executive-scorecard", headers=admin_headers)
        assert score_resp.status_code == 200
        data = score_resp.json()
        assert data["cycle_id"] == cycle_id
        assert "service" in data
        assert "cost" in data
        assert "cash" in data
        assert "risk" in data
        assert "decision_signal" in data

    def test_get_executive_scorecard_without_matching_scenario_period(self, client: TestClient, admin_headers):
        cycle_resp = client.post(
            "/api/v1/sop-cycles/",
            headers=admin_headers,
            json={
                "cycle_name": "No Scenario Match",
                "period": "2026-11-01",
            },
        )
        assert cycle_resp.status_code == 201
        cycle_id = cycle_resp.json()["id"]

        score_resp = client.get(f"/api/v1/sop-cycles/{cycle_id}/executive-scorecard", headers=admin_headers)
        assert score_resp.status_code == 200
        data = score_resp.json()
        assert data["cycle_id"] == cycle_id
        assert data["service"]["baseline_service_level"] == 0
        assert data["service"]["scenario_service_level"] == 0
