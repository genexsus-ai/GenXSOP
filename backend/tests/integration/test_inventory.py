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

    def test_create_inventory(self, client: TestClient, admin_headers, product):
        resp = client.post("/api/v1/inventory/", headers=admin_headers, json={
            "product_id": product.id,
            "location": "Warehouse B",
            "on_hand_qty": 150.0,
            "safety_stock": 30.0,
            "reorder_point": 60.0,
            "max_stock": 500.0,
            "unit_cost": 100.0,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["product_id"] == product.id
        assert float(data["on_hand_qty"]) == 150.0

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
        assert resp.status_code == 401


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

    def test_adjust_inventory_quantity(self, client: TestClient, admin_headers, inventory):
        resp = client.post(
            f"/api/v1/inventory/{inventory.id}/adjust",
            headers=admin_headers,
            json={
                "adjustment_qty": 50.0,
                "reason": "Physical count correction",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        # on_hand_qty should be updated
        assert float(data["on_hand_qty"]) == float(inventory.on_hand_qty) + 50.0

    def test_adjust_inventory_negative(self, client: TestClient, admin_headers, inventory):
        resp = client.post(
            f"/api/v1/inventory/{inventory.id}/adjust",
            headers=admin_headers,
            json={
                "adjustment_qty": -20.0,
                "reason": "Damaged goods removal",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert float(data["on_hand_qty"]) == float(inventory.on_hand_qty) - 20.0
