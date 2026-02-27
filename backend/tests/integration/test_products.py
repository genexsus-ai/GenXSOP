"""
Integration Tests — Products & Categories Endpoints

Tests:
- GET/POST/PUT/DELETE /api/v1/products
- GET/POST /api/v1/products/categories
- Authorization: unauthenticated access blocked
- Duplicate SKU returns 409
"""
import pytest
from fastapi.testclient import TestClient


class TestCategories:

    def test_create_category(self, client: TestClient, admin_headers):
        resp = client.post("/api/v1/products/categories", headers=admin_headers, json={
            "name": "Electronics",
            "description": "Electronic goods",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Electronics"
        assert "id" in data

    def test_list_categories(self, client: TestClient, admin_headers, category):
        resp = client.get("/api/v1/products/categories", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list) or "items" in data

    def test_create_category_unauthenticated_returns_401(self, client: TestClient):
        resp = client.post("/api/v1/products/categories", json={"name": "Test"})
        assert resp.status_code == 401


class TestProducts:

    def test_create_product(self, client: TestClient, admin_headers, category):
        resp = client.post("/api/v1/products/", headers=admin_headers, json={
            "sku": "SKU-TEST-001",
            "name": "Test Widget",
            "category_id": category.id,
            "unit_cost": 50.00,
            "unit_price": 80.00,
            "lead_time_days": 7,
            "status": "active",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["sku"] == "SKU-TEST-001"
        assert data["name"] == "Test Widget"
        assert "id" in data

    def test_create_product_duplicate_sku_returns_409(self, client: TestClient, admin_headers, product):
        resp = client.post("/api/v1/products/", headers=admin_headers, json={
            "sku": "SKU-001",  # already exists
            "name": "Duplicate SKU Product",
            "category_id": product.category_id,
            "unit_cost": 10.00,
            "unit_price": 20.00,
            "lead_time_days": 5,
            "status": "active",
        })
        assert resp.status_code == 409

    def test_list_products(self, client: TestClient, admin_headers, product):
        resp = client.get("/api/v1/products/", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        items = data.get("items", data) if isinstance(data, dict) else data
        assert len(items) >= 1

    def test_get_product_by_id(self, client: TestClient, admin_headers, product):
        resp = client.get(f"/api/v1/products/{product.id}", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == product.id
        assert data["sku"] == "SKU-001"

    def test_get_nonexistent_product_returns_404(self, client: TestClient, admin_headers):
        resp = client.get("/api/v1/products/99999", headers=admin_headers)
        assert resp.status_code == 404

    def test_update_product(self, client: TestClient, admin_headers, product):
        resp = client.put(f"/api/v1/products/{product.id}", headers=admin_headers, json={
            "name": "Updated Product Name",
            "unit_price": 200.00,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Updated Product Name"

    def test_delete_product(self, client: TestClient, admin_headers, category):
        # Create a product to delete
        create_resp = client.post("/api/v1/products/", headers=admin_headers, json={
            "sku": "SKU-DELETE-001",
            "name": "To Delete",
            "category_id": category.id,
            "unit_cost": 10.00,
            "unit_price": 15.00,
            "lead_time_days": 3,
            "status": "active",
        })
        assert create_resp.status_code == 201
        product_id = create_resp.json()["id"]

        del_resp = client.delete(f"/api/v1/products/{product_id}", headers=admin_headers)
        assert del_resp.status_code in (200, 204)

    def test_list_products_unauthenticated_returns_401(self, client: TestClient):
        resp = client.get("/api/v1/products/")
        assert resp.status_code == 401

    def test_create_product_missing_required_fields_returns_422(self, client: TestClient, admin_headers):
        resp = client.post("/api/v1/products/", headers=admin_headers, json={
            "name": "No SKU Product",
        })
        assert resp.status_code == 422
