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
    assert first_body["retry_count"] == 0
    assert first_body["max_retries"] == 3
    assert first_body["out_of_order"] is False

    duplicate = client.post(
        "/api/v1/integrations/events/ingest",
        headers=admin_headers,
        json=payload,
    )
    assert duplicate.status_code == 200
    dup_body = duplicate.json()
    assert dup_body["duplicate"] is True
    assert dup_body["duplicate_of_event_id"] == "evt-001"
    assert dup_body["retry_count"] == 0

    replay = client.post(
        "/api/v1/integrations/events/evt-001/replay",
        headers=admin_headers,
    )
    assert replay.status_code == 200
    replay_body = replay.json()
    assert replay_body["event_id"] == "evt-001"
    assert replay_body["processing_status"] == "REPLAYED"
    assert replay_body["replay_count"] == 1
    assert replay_body["retry_count"] == 1

    recent = client.get(
        "/api/v1/integrations/events?limit=10",
        headers=admin_headers,
    )
    assert recent.status_code == 200
    items = recent.json()
    assert any(i["event_id"] == "evt-001" for i in items)


def test_canonical_event_out_of_order_and_retry_budget_dead_letter_context(client: TestClient, db):
    admin_headers = _auth_headers(db, "admin5@test.com", "admin")

    newer = {
        "event_id": "evt-new",
        "event_type": "MACHINE_DOWN",
        "event_source": "MES",
        "event_timestamp": "2026-03-01T10:10:00Z",
        "plant_id": "plant-1",
        "line_id": "line-2",
        "resource_id": "mc-22",
        "severity": "high",
        "payload": {"reason": "trip"},
        "idempotency_key": "idem-new",
        "max_retries": 1,
    }
    older = {
        "event_id": "evt-old",
        "event_type": "MACHINE_RECOVERED",
        "event_source": "MES",
        "event_timestamp": "2026-03-01T10:00:00Z",
        "plant_id": "plant-1",
        "line_id": "line-2",
        "resource_id": "mc-22",
        "severity": "medium",
        "payload": {"reason": "restored"},
        "idempotency_key": "idem-old",
        "max_retries": 1,
    }

    first = client.post("/api/v1/integrations/events/ingest", headers=admin_headers, json=newer)
    assert first.status_code == 200

    second = client.post("/api/v1/integrations/events/ingest", headers=admin_headers, json=older)
    assert second.status_code == 200
    old_body = second.json()
    assert old_body["out_of_order"] is True

    replay_1 = client.post("/api/v1/integrations/events/evt-old/replay", headers=admin_headers)
    assert replay_1.status_code == 200
    assert replay_1.json()["processing_status"] == "REPLAYED"

    replay_2 = client.post("/api/v1/integrations/events/evt-old/replay", headers=admin_headers)
    assert replay_2.status_code == 200
    second_replay = replay_2.json()
    assert second_replay["processing_status"] == "FAILED"
    assert second_replay["retry_count"] == 2

    listed = client.get("/api/v1/integrations/events?limit=20", headers=admin_headers)
    assert listed.status_code == 200
    old_row = next(i for i in listed.json() if i["event_id"] == "evt-old")
    assert old_row["dead_letter_reason"] is not None


def test_agentic_config_objectives_and_policies_defaults_and_upsert(client: TestClient, db):
    admin_headers = _auth_headers(db, "admin6@test.com", "admin")

    get_obj = client.get("/api/v1/config/objectives", headers=admin_headers)
    assert get_obj.status_code == 200
    obj_body = get_obj.json()
    assert obj_body["config_type"] == "objectives"
    assert obj_body["config"]["tardiness"] == 0.45

    put_obj = client.put(
        "/api/v1/config/objectives",
        headers=admin_headers,
        json={
            "scope": "global",
            "name": "default",
            "config": {
                "tardiness": 0.5,
                "changeover": 0.2,
                "utilization": 0.3,
            },
        },
    )
    assert put_obj.status_code == 200
    put_obj_body = put_obj.json()
    assert put_obj_body["config"]["tardiness"] == 0.5
    assert put_obj_body["version"] >= 1

    get_pol = client.get("/api/v1/config/policies", headers=admin_headers)
    assert get_pol.status_code == 200
    pol_body = get_pol.json()
    assert pol_body["config_type"] == "policies"
    assert pol_body["config"]["maker_checker_required"] is True


def test_agentic_config_upsert_forbidden_for_non_privileged_role(client: TestClient, db):
    planner_headers = _auth_headers(db, "planner2@test.com", "demand_planner")

    resp = client.put(
        "/api/v1/config/policies",
        headers=planner_headers,
        json={
            "scope": "global",
            "name": "default",
            "config": {
                "auto_publish": True,
                "maker_checker_required": False,
            },
        },
    )
    assert resp.status_code == 403
