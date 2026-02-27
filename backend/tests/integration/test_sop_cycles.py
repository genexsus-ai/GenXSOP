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
            "name": "March 2026 S&OP",
            "period_start": "2026-03-01",
            "period_end": "2026-03-31",
            "notes": "Monthly S&OP cycle",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "March 2026 S&OP"
        assert data["current_step"] == 1
        assert data["status"] == "active"
        assert "id" in data

    def test_list_sop_cycles(self, client: TestClient, admin_headers):
        client.post("/api/v1/sop-cycles/", headers=admin_headers, json={
            "name": "April 2026 S&OP",
            "period_start": "2026-04-01",
            "period_end": "2026-04-30",
        })
        resp = client.get("/api/v1/sop-cycles/", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        items = data.get("items", data) if isinstance(data, dict) else data
        assert len(items) >= 1

    def test_get_sop_cycle_by_id(self, client: TestClient, admin_headers):
        create_resp = client.post("/api/v1/sop-cycles/", headers=admin_headers, json={
            "name": "Test Cycle",
            "period_start": "2026-05-01",
            "period_end": "2026-05-31",
        })
        cycle_id = create_resp.json()["id"]
        resp = client.get(f"/api/v1/sop-cycles/{cycle_id}", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == cycle_id

    def test_get_nonexistent_cycle_returns_404(self, client: TestClient, admin_headers):
        resp = client.get("/api/v1/sop-cycles/99999", headers=admin_headers)
        assert resp.status_code == 404

    def test_create_sop_cycle_unauthenticated_returns_401(self, client: TestClient):
        resp = client.post("/api/v1/sop-cycles/", json={
            "name": "Hack Cycle",
            "period_start": "2026-03-01",
            "period_end": "2026-03-31",
        })
        assert resp.status_code == 401


class TestSOPCycleStepAdvancement:

    def _create_cycle(self, client, headers):
        resp = client.post("/api/v1/sop-cycles/", headers=headers, json={
            "name": "Step Test Cycle",
            "period_start": "2026-06-01",
            "period_end": "2026-06-30",
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
        assert resp.json()["status"] == "completed"

    def test_get_cycle_steps(self, client: TestClient, admin_headers):
        cycle_id = self._create_cycle(client, admin_headers)
        resp = client.get(f"/api/v1/sop-cycles/{cycle_id}/steps", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, (list, dict))


class TestSOPCycleFilters:

    def test_filter_by_status(self, client: TestClient, admin_headers):
        client.post("/api/v1/sop-cycles/", headers=admin_headers, json={
            "name": "Active Cycle",
            "period_start": "2026-07-01",
            "period_end": "2026-07-31",
        })
        resp = client.get("/api/v1/sop-cycles/?status=active", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        items = data.get("items", data) if isinstance(data, dict) else data
        for item in items:
            assert item["status"] == "active"
