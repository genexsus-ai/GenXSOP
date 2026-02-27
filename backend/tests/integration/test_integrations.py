from fastapi.testclient import TestClient
from app.models.user import User
from app.utils.security import get_password_hash, create_access_token


def _auth_headers(db, email: str, role: str) -> dict:
    user = User(
        email=email,
        hashed_password=get_password_hash("Password123!"),
        full_name="Test User",
        role=role,
        department="IT",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role})
    return {"Authorization": f"Bearer {token}"}


def test_sync_products_requires_auth(client: TestClient):
    resp = client.post(
        "/api/v1/integrations/erp/products/sync",
        json={"meta": {"source_system": "ERP"}, "items": []},
    )
    assert resp.status_code == 403


def test_sync_products_forbidden_for_non_integration_role(client: TestClient, db):
    planner_headers = _auth_headers(db, "planner@test.com", "demand_planner")
    resp = client.post(
        "/api/v1/integrations/erp/products/sync",
        headers=planner_headers,
        json={"meta": {"source_system": "ERP"}, "items": []},
    )
    assert resp.status_code == 403


def test_sync_products_happy_path_admin(client: TestClient, db):
    admin_headers = _auth_headers(db, "admin@test.com", "admin")
    resp = client.post(
        "/api/v1/integrations/erp/products/sync",
        headers=admin_headers,
        json={
            "meta": {"source_system": "ERP", "batch_id": "b1"},
            "items": [{"sku": "INT-001", "name": "Integrated Product"}],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["processed"] == 1


def test_sync_inventory_happy_path_admin(client: TestClient, db):
    admin_headers = _auth_headers(db, "admin2@test.com", "admin")
    resp = client.post(
        "/api/v1/integrations/erp/inventory/sync",
        headers=admin_headers,
        json={
            "meta": {"source_system": "ERP"},
            "items": [
                {
                    "sku": "UNKNOWN-SKU",
                    "location": "Warehouse B",
                    "on_hand_qty": 100,
                    "allocated_qty": 5,
                    "in_transit_qty": 2,
                }
            ],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    assert resp.json()["skipped"] == 1


def test_publish_demand_plan_fails_when_not_approved(client: TestClient, db):
    admin_headers = _auth_headers(db, "admin3@test.com", "admin")
    resp = client.post(
        "/api/v1/integrations/erp/publish/demand-plan/99999",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is False
