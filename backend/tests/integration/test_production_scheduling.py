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

    def test_event_recommendation_persists_and_returns_orchestration(
        self,
        client: TestClient,
        admin_headers,
        supply_plan,
    ):
        # Ensure schedules exist for event scope.
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

        resp = client.post(
            "/api/v1/production-scheduling/events/recommendation",
            headers=admin_headers,
            json={
                "event_type": "MACHINE_DOWN",
                "severity": "high",
                "event_timestamp": "2026-03-01T10:00:00Z",
                "supply_plan_id": supply_plan.id,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["recommendation_id"]
        assert data["workflow_id"]
        assert data["state"] == "PENDING_APPROVAL"
        assert isinstance(data["actions"], list)
        assert data["orchestration"] is not None
        assert data["orchestration"]["workflow_state"] in ["SIMULATED", "FAILED"]
        assert "objective_weights" in data["orchestration"]
        assert isinstance(data["orchestration"]["alternatives"], list)
        if data["orchestration"]["alternatives"]:
            alt = data["orchestration"]["alternatives"][0]
            assert "risk_indicators" in alt
            assert "schedule_adherence_delta_pct" in alt["simulated_kpis"]
            assert "wip_delta_pct" in alt["simulated_kpis"]

        list_resp = client.get(
            f"/api/v1/production-scheduling/recommendations?supply_plan_id={supply_plan.id}",
            headers=admin_headers,
        )
        assert list_resp.status_code == 200
        recs = list_resp.json()
        assert any(r["recommendation_id"] == data["recommendation_id"] for r in recs)

    def test_approve_and_reject_recommendation_flow(
        self,
        client: TestClient,
        admin_headers,
        supply_plan,
    ):
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

        create_resp = client.post(
            "/api/v1/production-scheduling/events/recommendation",
            headers=admin_headers,
            json={
                "event_type": "ORDER_PRIORITY_CHANGED",
                "severity": "medium",
                "event_timestamp": "2026-03-01T11:00:00Z",
                "supply_plan_id": supply_plan.id,
            },
        )
        rec_id = create_resp.json()["recommendation_id"]

        approve_resp = client.post(
            f"/api/v1/production-scheduling/recommendations/{rec_id}/approve",
            headers=admin_headers,
            json={"note": "Looks good"},
        )
        assert approve_resp.status_code == 200
        approved = approve_resp.json()
        assert approved["status"] == "approved"
        assert approved["state"] == "APPROVED"

        # Invalid transition should fail with explicit guardrail.
        approve_again = client.post(
            f"/api/v1/production-scheduling/recommendations/{rec_id}/approve",
            headers=admin_headers,
            json={"note": "again"},
        )
        assert approve_again.status_code == 400

        # Second decision should fail due to guardrail.
        reject_again = client.post(
            f"/api/v1/production-scheduling/recommendations/{rec_id}/reject",
            headers=admin_headers,
            json={"note": "Too late"},
        )
        assert reject_again.status_code == 400

    def test_publish_requires_approved_transition_guard(self, client: TestClient, admin_headers, supply_plan):
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

        create_resp = client.post(
            "/api/v1/production-scheduling/events/recommendation",
            headers=admin_headers,
            json={
                "event_type": "MACHINE_DOWN",
                "severity": "high",
                "event_timestamp": "2026-03-01T11:30:00Z",
                "supply_plan_id": supply_plan.id,
            },
        )
        rec_id = create_resp.json()["recommendation_id"]

        publish_without_approve = client.post(
            f"/api/v1/production-scheduling/recommendations/{rec_id}/publish",
            headers=admin_headers,
            json={"note": "should fail", "apply_actions": True},
        )
        assert publish_without_approve.status_code == 400

    def test_phase1_extended_event_types_generate_expected_actions(self, client: TestClient, admin_headers, supply_plan):
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

        downtime = client.post(
            "/api/v1/production-scheduling/events/recommendation",
            headers=admin_headers,
            json={
                "event_type": "DOWNTIME_PLANNED",
                "severity": "medium",
                "event_timestamp": "2026-03-01T13:00:00Z",
                "supply_plan_id": supply_plan.id,
            },
        )
        assert downtime.status_code == 200
        assert downtime.json()["actions"][0]["action_type"] == "hold"

        released = client.post(
            "/api/v1/production-scheduling/events/recommendation",
            headers=admin_headers,
            json={
                "event_type": "ORDER_RELEASED",
                "severity": "medium",
                "event_timestamp": "2026-03-01T13:10:00Z",
                "supply_plan_id": supply_plan.id,
            },
        )
        assert released.status_code == 200
        assert released.json()["actions"][0]["action_type"] == "expedite"

        wip = client.post(
            "/api/v1/production-scheduling/events/recommendation",
            headers=admin_headers,
            json={
                "event_type": "WIP_UPDATED",
                "severity": "low",
                "event_timestamp": "2026-03-01T13:20:00Z",
                "supply_plan_id": supply_plan.id,
            },
        )
        assert wip.status_code == 200
        assert wip.json()["actions"][0]["action_type"] == "resequence"

    def test_recommendations_stream_requires_access_token(
        self,
        client: TestClient,
    ):
        resp = client.get("/api/v1/production-scheduling/recommendations-stream")
        assert resp.status_code == 422

    def test_modify_publish_and_version_compare_flow(
        self,
        client: TestClient,
        admin_headers,
        supply_plan,
    ):
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

        create_resp = client.post(
            "/api/v1/production-scheduling/events/recommendation",
            headers=admin_headers,
            json={
                "event_type": "MACHINE_DOWN",
                "severity": "high",
                "event_timestamp": "2026-03-01T12:00:00Z",
                "supply_plan_id": supply_plan.id,
            },
        )
        assert create_resp.status_code == 200
        base_rec_id = create_resp.json()["recommendation_id"]

        modify_resp = client.post(
            f"/api/v1/production-scheduling/recommendations/{base_rec_id}/modify",
            headers=admin_headers,
            json={
                "note": "planner revised",
                "recommendation_summary": "Planner-updated summary",
                "actions": [
                    {
                        "action_type": "resequence",
                        "schedule_id": 1,
                        "from_sequence": 1,
                        "to_sequence": 2,
                        "reason": "manual tweak",
                        "confidence": 0.71,
                    }
                ],
            },
        )
        assert modify_resp.status_code == 200
        modified = modify_resp.json()
        assert modified["source_recommendation_id"] == base_rec_id
        assert modified["revision_number"] >= 2

        approve_resp = client.post(
            f"/api/v1/production-scheduling/recommendations/{modified['recommendation_id']}/approve",
            headers=admin_headers,
            json={"note": "approved for publish"},
        )
        assert approve_resp.status_code == 200
        assert approve_resp.json()["status"] == "approved"

        publish_resp = client.post(
            f"/api/v1/production-scheduling/recommendations/{modified['recommendation_id']}/publish",
            headers=admin_headers,
            json={"note": "publish now", "apply_actions": True},
        )
        assert publish_resp.status_code == 200
        published = publish_resp.json()
        assert published["status"] == "published"
        assert published["state"] == "PUBLISHED"
        assert published["published_at"] is not None

        versions_resp = client.get(
            f"/api/v1/production-scheduling/schedule-versions?supply_plan_id={supply_plan.id}",
            headers=admin_headers,
        )
        assert versions_resp.status_code == 200
        versions = versions_resp.json()
        assert len(versions) >= 1

        compare_resp = client.get(
            (
                f"/api/v1/production-scheduling/schedule-versions/compare"
                f"?supply_plan_id={supply_plan.id}&base_version=1&target_version=1"
            ),
            headers=admin_headers,
        )
        assert compare_resp.status_code == 200
        compare_data = compare_resp.json()
        assert compare_data["supply_plan_id"] == supply_plan.id
        assert compare_data["base_version"] == 1
        assert compare_data["target_version"] == 1
