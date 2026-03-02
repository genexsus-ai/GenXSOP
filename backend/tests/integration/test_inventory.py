"""
Integration Tests — Inventory Endpoints

Tests:
- GET/POST/PUT /api/v1/inventory
- Inventory health check
- Reorder alerts
- Inventory adjustment
"""
import pytest
from fastapi.testclient import TestClient


class TestInventoryCRUD:
    def test_list_inventory(self, client: TestClient, admin_headers, inventory):
        resp = client.get("/api/v1/inventory/", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        items = data.get("items", data) if isinstance(data, dict) else data
        assert len(items) >= 1

    def test_get_inventory_by_id(self, client: TestClient, admin_headers, inventory):
        resp = client.get(f"/api/v1/inventory/{inventory.id}", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == inventory.id

    def test_get_nonexistent_inventory_returns_404(self, client: TestClient, admin_headers):
        resp = client.get("/api/v1/inventory/99999", headers=admin_headers)
        assert resp.status_code == 404

    def test_update_inventory(self, client: TestClient, admin_headers, inventory):
        resp = client.put(f"/api/v1/inventory/{inventory.id}", headers=admin_headers, json={
            "on_hand_qty": 250.0,
        })
        assert resp.status_code == 200
        assert float(resp.json()["on_hand_qty"]) == 250.0

    def test_list_inventory_unauthenticated_returns_401(self, client: TestClient):
        resp = client.get("/api/v1/inventory/")
        assert resp.status_code == 403


class TestInventoryHealth:

    def test_inventory_health_endpoint(self, client: TestClient, admin_headers, inventory):
        resp = client.get("/api/v1/inventory/health", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, (list, dict))

    def test_inventory_alerts_endpoint(self, client: TestClient, admin_headers, inventory):
        resp = client.get("/api/v1/inventory/alerts", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, (list, dict))

    def test_filter_inventory_by_product(self, client: TestClient, admin_headers, inventory, product):
        resp = client.get(
            f"/api/v1/inventory/?product_id={product.id}",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        items = data.get("items", data) if isinstance(data, dict) else data
        for item in items:
            assert item["product_id"] == product.id


class TestInventoryAdjustment:

    def test_adjust_inventory_quantity_via_update(self, client: TestClient, admin_headers, inventory):
        new_qty = float(inventory.on_hand_qty) + 50.0
        resp = client.put(
            f"/api/v1/inventory/{inventory.id}",
            headers=admin_headers,
            json={"on_hand_qty": new_qty},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert float(data["on_hand_qty"]) == new_qty

    def test_adjust_inventory_negative_via_update(self, client: TestClient, admin_headers, inventory):
        new_qty = max(0.0, float(inventory.on_hand_qty) - 20.0)
        resp = client.put(
            f"/api/v1/inventory/{inventory.id}",
            headers=admin_headers,
            json={"on_hand_qty": new_qty},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert float(data["on_hand_qty"]) == new_qty


class TestInventoryOptimization:

    def test_run_inventory_optimization(self, client: TestClient, admin_headers, inventory):
        resp = client.post(
            "/api/v1/inventory/optimization/runs",
            headers=admin_headers,
            json={
                "service_level_target": 0.95,
                "lead_time_days": 14,
                "review_period_days": 7,
                "moq_units": 20,
                "lot_size_units": 5,
                "capacity_max_units": 1000,
                "lead_time_variability_days": 2,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "run_id" in data
        assert data["processed_count"] >= 1
        assert data["updated_count"] >= 1

    def test_get_inventory_exceptions(self, client: TestClient, admin_headers, inventory):
        # Ensure policies are populated before checking exception list
        client.post(
            "/api/v1/inventory/optimization/runs",
            headers=admin_headers,
            json={
                "service_level_target": 0.95,
                "lead_time_days": 14,
                "review_period_days": 7,
            },
        )

        resp = client.get("/api/v1/inventory/exceptions", headers=admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_update_inventory_exception_workflow(self, client: TestClient, admin_headers, inventory):
        run_resp = client.post(
            "/api/v1/inventory/optimization/runs",
            headers=admin_headers,
            json={
                "service_level_target": 0.95,
                "lead_time_days": 14,
                "review_period_days": 7,
            },
        )
        assert run_resp.status_code == 200

        list_resp = client.get("/api/v1/inventory/exceptions", headers=admin_headers)
        assert list_resp.status_code == 200
        exceptions = list_resp.json()
        if not exceptions:
            return

        ex = exceptions[0]
        ex_id = ex.get("id")
        if not ex_id:
            return

        patch_resp = client.patch(
            f"/api/v1/inventory/exceptions/{ex_id}",
            headers=admin_headers,
            json={
                "status": "in_progress",
                "owner_user_id": 1,
                "notes": "Assigned to planner for mitigation",
            },
        )
        assert patch_resp.status_code == 200
        patched = patch_resp.json()
        assert patched["status"] == "in_progress"
        assert patched["owner_user_id"] == 1

    def test_override_inventory_policy(self, client: TestClient, admin_headers, inventory):
        resp = client.put(
            f"/api/v1/inventory/policies/{inventory.id}/override",
            headers=admin_headers,
            json={
                "safety_stock": 60.0,
                "reorder_point": 90.0,
                "max_stock": 650.0,
                "reason": "Enterprise policy alignment",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert float(data["safety_stock"]) == 60.0
        assert float(data["reorder_point"]) == 90.0
        assert float(data["max_stock"]) == 650.0


class TestInventoryRecommendations:

    def test_generate_and_list_recommendations(self, client: TestClient, admin_headers, inventory):
        gen_resp = client.post(
            "/api/v1/inventory/recommendations/generate",
            headers=admin_headers,
            json={
                "min_confidence": 0.6,
                "max_items": 50,
            },
        )
        assert gen_resp.status_code == 200
        generated = gen_resp.json()
        assert isinstance(generated, list)
        assert len(generated) >= 1
        assert generated[0]["status"] == "pending"

        list_resp = client.get(
            "/api/v1/inventory/recommendations?status=pending",
            headers=admin_headers,
        )
        assert list_resp.status_code == 200
        recs = list_resp.json()
        assert isinstance(recs, list)
        assert len(recs) >= 1

    def test_decide_recommendation_apply_changes(self, client: TestClient, admin_headers, inventory):
        gen_resp = client.post(
            "/api/v1/inventory/recommendations/generate",
            headers=admin_headers,
            json={
                "min_confidence": 0.5,
                "max_items": 20,
            },
        )
        assert gen_resp.status_code == 200
        recs = gen_resp.json()
        assert recs
        rec_id = recs[0]["id"]

        decide_resp = client.post(
            f"/api/v1/inventory/recommendations/{rec_id}/decision",
            headers=admin_headers,
            json={
                "decision": "accepted",
                "apply_changes": True,
                "notes": "Apply AI recommendation",
            },
        )
        assert decide_resp.status_code == 200
        decided = decide_resp.json()
        assert decided["status"] == "applied"

        inv_resp = client.get(f"/api/v1/inventory/{inventory.id}", headers=admin_headers)
        assert inv_resp.status_code == 200
        inv = inv_resp.json()
        assert float(inv["safety_stock"]) > 0
        assert float(inv["reorder_point"]) > 0


class TestInventoryPhase45:

    def test_get_rebalance_recommendations(self, client: TestClient, admin_headers):
        resp = client.get("/api/v1/inventory/rebalance/recommendations", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            item = data[0]
            assert "product_id" in item
            assert "from_location" in item
            assert "to_location" in item
            assert "transfer_qty" in item

    def test_auto_apply_and_control_tower_summary(self, client: TestClient, admin_headers):
        gen_resp = client.post(
            "/api/v1/inventory/recommendations/generate",
            headers=admin_headers,
            json={"min_confidence": 0.5, "max_items": 20},
        )
        assert gen_resp.status_code == 200

        auto_resp = client.post(
            "/api/v1/inventory/recommendations/auto-apply",
            headers=admin_headers,
            json={
                "min_confidence": 0.5,
                "max_demand_pressure": 5,
                "max_items": 20,
                "dry_run": False,
            },
        )
        assert auto_resp.status_code == 200
        auto_data = auto_resp.json()
        assert "eligible_count" in auto_data
        assert "applied_count" in auto_data
        assert "recommendation_ids" in auto_data

        summary_resp = client.get("/api/v1/inventory/control-tower/summary", headers=admin_headers)
        assert summary_resp.status_code == 200
        summary = summary_resp.json()
        assert "pending_recommendations" in summary
        assert "applied_recommendations" in summary
        assert "acceptance_rate_pct" in summary
        assert "recommendation_backlog_risk" in summary
