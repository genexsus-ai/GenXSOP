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


def test_canonical_event_ingest_duplicate_and_replay_flow(client: TestClient, db):
    admin_headers = _auth_headers(db, "admin4@test.com", "admin")

    payload = {
        "event_id": "evt-001",
        "event_type": "MACHINE_DOWN",
        "event_source": "MES",
        "event_timestamp": "2026-03-01T10:00:00Z",
        "plant_id": "plant-1",
        "line_id": "line-2",
        "resource_id": "mc-22",
        "severity": "high",
        "payload": {"workcenter": "WC-2", "line": "Line-2", "reason": "overheat"},
        "correlation_id": "corr-abc",
        "trace_id": "trace-xyz",
        "idempotency_key": "idem-001",
    }

    first = client.post(
        "/api/v1/integrations/events/ingest",
        headers=admin_headers,
        json=payload,
    )
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["event_id"] == "evt-001"
    assert first_body["duplicate"] is False
    assert first_body["processing_status"] == "NORMALIZED"

    duplicate = client.post(
        "/api/v1/integrations/events/ingest",
        headers=admin_headers,
        json=payload,
    )
    assert duplicate.status_code == 200
    dup_body = duplicate.json()
    assert dup_body["duplicate"] is True
    assert dup_body["duplicate_of_event_id"] == "evt-001"

    replay = client.post(
        "/api/v1/integrations/events/evt-001/replay",
        headers=admin_headers,
    )
    assert replay.status_code == 200
    replay_body = replay.json()
    assert replay_body["event_id"] == "evt-001"
    assert replay_body["processing_status"] == "REPLAYED"
    assert replay_body["replay_count"] == 1

    recent = client.get(
        "/api/v1/integrations/events?limit=10",
        headers=admin_headers,
    )
    assert recent.status_code == 200
    items = recent.json()
    assert any(i["event_id"] == "evt-001" for i in items)
