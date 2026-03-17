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


def test_audit_recommendation_trail_endpoint_returns_revisions(client: TestClient, db):
    admin_headers = _auth_headers(db, "admin7@test.com", "admin")

    # Create minimum master data/supply plan so recommendation flow can run in this test module.
    product_sync = client.post(
        "/api/v1/integrations/erp/products/sync",
        headers=admin_headers,
        json={
            "meta": {"source_system": "ERP"},
            "items": [{"sku": "AUD-001", "name": "Audit Product"}],
        },
    )
    assert product_sync.status_code == 200

    from datetime import date
    from app.models.product import Product
    from app.models.supply_plan import SupplyPlan

    product = db.query(Product).filter(Product.sku == "AUD-001").first()
    assert product is not None

    plan = SupplyPlan(
        product_id=product.id,
        period=date(2026, 3, 1),
        planned_prod_qty=100,
        status="draft",
        created_by=1,
        version=1,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    gen = client.post(
        "/api/v1/production-scheduling/generate",
        headers=admin_headers,
        json={
            "supply_plan_id": plan.id,
            "workcenters": ["WC-1"],
            "lines": ["Line-1"],
            "shifts": ["Shift-A"],
        },
    )
    assert gen.status_code == 201

    rec = client.post(
        "/api/v1/production-scheduling/events/recommendation",
        headers=admin_headers,
        json={
            "event_type": "MACHINE_DOWN",
            "severity": "high",
            "event_timestamp": "2026-03-01T10:00:00Z",
            "supply_plan_id": plan.id,
        },
    )
    assert rec.status_code == 200
    rec_id = rec.json()["recommendation_id"]

    trail = client.get(f"/api/v1/audit/recommendations/{rec_id}", headers=admin_headers)
    assert trail.status_code == 200
    body = trail.json()
    assert body["recommendation_id"] == rec_id
    assert len(body["revisions"]) >= 1
    assert body["revisions"][0]["recommendation_id"] == rec_id


def test_audit_decisions_endpoint_accessible_and_filterable(client: TestClient, db):
    admin_headers = _auth_headers(db, "admin8@test.com", "admin")

    resp = client.get("/api/v1/audit/decisions?limit=10", headers=admin_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_simulation_run_and_get_by_id_from_recommendation(client: TestClient, db):
    admin_headers = _auth_headers(db, "admin9@test.com", "admin")

    product_sync = client.post(
        "/api/v1/integrations/erp/products/sync",
        headers=admin_headers,
        json={
            "meta": {"source_system": "ERP"},
            "items": [{"sku": "SIM-001", "name": "Simulation Product"}],
        },
    )
    assert product_sync.status_code == 200

    from datetime import date
    from app.models.product import Product
    from app.models.supply_plan import SupplyPlan

    product = db.query(Product).filter(Product.sku == "SIM-001").first()
    assert product is not None

    plan = SupplyPlan(
        product_id=product.id,
        period=date(2026, 3, 1),
        planned_prod_qty=120,
        status="draft",
        created_by=1,
        version=1,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    gen = client.post(
        "/api/v1/production-scheduling/generate",
        headers=admin_headers,
        json={
            "supply_plan_id": plan.id,
            "workcenters": ["WC-1"],
            "lines": ["Line-1"],
            "shifts": ["Shift-A"],
        },
    )
    assert gen.status_code == 201

    rec = client.post(
        "/api/v1/production-scheduling/events/recommendation",
        headers=admin_headers,
        json={
            "event_type": "MACHINE_DOWN",
            "severity": "high",
            "event_timestamp": "2026-03-01T10:00:00Z",
            "supply_plan_id": plan.id,
        },
    )
    assert rec.status_code == 200
    rec_id = rec.json()["recommendation_id"]

    run = client.post(
        "/api/v1/simulations",
        headers=admin_headers,
        json={
            "recommendation_id": rec_id,
            "scenario_name": "throughput-what-if",
        },
    )
    assert run.status_code == 200
    run_body = run.json()
    assert run_body["recommendation_id"] == rec_id
    assert run_body["scenario_name"] == "throughput-what-if"
    assert run_body["status"] in {"completed", "failed"}
    assert run_body["simulation_id"]
    assert run_body["result"] is not None

    sim_id = run_body["simulation_id"]
    fetched = client.get(f"/api/v1/simulations/{sim_id}", headers=admin_headers)
    assert fetched.status_code == 200
    fetched_body = fetched.json()
    assert fetched_body["simulation_id"] == sim_id
    assert fetched_body["recommendation_id"] == rec_id


def test_simulation_direct_input_mode(client: TestClient, db):
    admin_headers = _auth_headers(db, "admin10@test.com", "admin")

    run = client.post(
        "/api/v1/simulations",
        headers=admin_headers,
        json={
            "scenario_name": "direct-input",
            "event_type": "MATERIAL_SHORTAGE",
            "severity": "medium",
            "action": {
                "action_type": "resequence",
                "schedule_id": 1,
                "from_sequence": 4,
                "to_sequence": 2,
                "reason": "material rebalancing",
                "confidence": 0.8,
            },
        },
    )
    assert run.status_code == 200
    body = run.json()
    assert body["simulation_id"]
    assert body["recommendation_id"] is None
    assert body["scenario_name"] == "direct-input"


def test_simulation_list_filters(client: TestClient, db):
    admin_headers = _auth_headers(db, "admin11@test.com", "admin")

    first = client.post(
        "/api/v1/simulations",
        headers=admin_headers,
        json={
            "scenario_name": "hist-alpha",
            "event_type": "MATERIAL_SHORTAGE",
            "severity": "medium",
            "action": {
                "action_type": "resequence",
                "schedule_id": 1,
                "from_sequence": 5,
                "to_sequence": 3,
                "reason": "alpha",
                "confidence": 0.75,
            },
        },
    )
    assert first.status_code == 200
    first_body = first.json()

    second = client.post(
        "/api/v1/simulations",
        headers=admin_headers,
        json={
            "scenario_name": "hist-beta",
            "event_type": "MACHINE_DOWN",
            "severity": "high",
            "action": {
                "action_type": "hold",
                "schedule_id": 1,
                "from_sequence": 2,
                "to_sequence": 2,
                "reason": "beta",
                "confidence": 0.7,
            },
        },
    )
    assert second.status_code == 200

    by_scenario = client.get(
        "/api/v1/simulations?scenario_name=hist-alpha",
        headers=admin_headers,
    )
    assert by_scenario.status_code == 200
    scenario_rows = by_scenario.json()
    assert len(scenario_rows) >= 1
    assert all(r["scenario_name"] == "hist-alpha" for r in scenario_rows)

    status_value = first_body["status"]
    by_status = client.get(
        f"/api/v1/simulations?status={status_value}",
        headers=admin_headers,
    )
    assert by_status.status_code == 200
    status_rows = by_status.json()
    assert len(status_rows) >= 1
    assert all(r["status"] == status_value for r in status_rows)

    limited = client.get("/api/v1/simulations?limit=1", headers=admin_headers)
    assert limited.status_code == 200
    assert len(limited.json()) == 1
