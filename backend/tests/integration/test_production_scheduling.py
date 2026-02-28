"""
Integration Tests — Production Scheduling Endpoints

Tests:
- POST /api/v1/production-scheduling/generate
- GET /api/v1/production-scheduling/schedules
- PATCH /api/v1/production-scheduling/schedules/{id}/status
"""

from fastapi.testclient import TestClient


class TestProductionScheduling:
    def test_generate_schedule(self, client: TestClient, admin_headers, supply_plan):
        resp = client.post(
            "/api/v1/production-scheduling/generate",
            headers=admin_headers,
            json={
                "supply_plan_id": supply_plan.id,
                "workcenters": ["WC-1", "WC-2"],
                "lines": ["Line-1"],
                "shifts": ["Shift-A", "Shift-B"],
                "duration_hours_per_slot": 8,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert len(data) == 4  # 2 workcenters x 1 line x 2 shifts
        assert all(item["supply_plan_id"] == supply_plan.id for item in data)
        assert all(float(item["planned_qty"]) >= 0 for item in data)

    def test_list_schedules_filtered_by_supply_plan(self, client: TestClient, admin_headers, supply_plan):
        client.post(
            "/api/v1/production-scheduling/generate",
            headers=admin_headers,
            json={
                "supply_plan_id": supply_plan.id,
                "workcenters": ["WC-1"],
                "lines": ["Line-1"],
                "shifts": ["Shift-A"],
            },
        )

        resp = client.get(
            f"/api/v1/production-scheduling/schedules?supply_plan_id={supply_plan.id}",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert all(item["supply_plan_id"] == supply_plan.id for item in data)

    def test_update_schedule_status(self, client: TestClient, admin_headers, supply_plan):
        create_resp = client.post(
            "/api/v1/production-scheduling/generate",
            headers=admin_headers,
            json={
                "supply_plan_id": supply_plan.id,
                "workcenters": ["WC-1"],
                "lines": ["Line-1"],
                "shifts": ["Shift-A"],
            },
        )
        schedule_id = create_resp.json()[0]["id"]

        resp = client.patch(
            f"/api/v1/production-scheduling/schedules/{schedule_id}/status",
            headers=admin_headers,
            json={"status": "released"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "released"

    def test_capacity_summary(self, client: TestClient, admin_headers, supply_plan):
        client.post(
            "/api/v1/production-scheduling/generate",
            headers=admin_headers,
            json={
                "supply_plan_id": supply_plan.id,
                "workcenters": ["WC-1"],
                "lines": ["Line-1"],
                "shifts": ["Shift-A", "Shift-B"],
            },
        )

        resp = client.get(
            f"/api/v1/production-scheduling/capacity-summary?supply_plan_id={supply_plan.id}",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["supply_plan_id"] == supply_plan.id
        assert data["slot_count"] == 2
        assert isinstance(data["groups"], list)

    def test_resequence_schedule(self, client: TestClient, admin_headers, supply_plan):
        create_resp = client.post(
            "/api/v1/production-scheduling/generate",
            headers=admin_headers,
            json={
                "supply_plan_id": supply_plan.id,
                "workcenters": ["WC-1"],
                "lines": ["Line-1"],
                "shifts": ["Shift-A", "Shift-B"],
            },
        )
        rows = create_resp.json()
        second_id = rows[1]["id"]

        resp = client.post(
            f"/api/v1/production-scheduling/schedules/{second_id}/resequence",
            headers=admin_headers,
            json={"direction": "up"},
        )
        assert resp.status_code == 200
        reordered = resp.json()
        assert reordered[0]["id"] == second_id
