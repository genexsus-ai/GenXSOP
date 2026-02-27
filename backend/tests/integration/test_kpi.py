"""
Integration Tests — KPI Endpoints

Tests:
- GET/POST/PUT /api/v1/kpi/metrics
- KPI summary
- KPI alerts
- KPI targets
"""
import pytest
from fastapi.testclient import TestClient


class TestKPIMetricCRUD:

    def test_create_kpi_metric(self, client: TestClient, admin_headers):
        resp = client.post("/api/v1/kpi/metrics", headers=admin_headers, json={
            "name": "Forecast Accuracy",
            "kpi_type": "forecast_accuracy",
            "period": "2026-03-01",
            "actual_value": 87.5,
            "target_value": 90.0,
            "unit": "percent",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Forecast Accuracy"
        assert float(data["actual_value"]) == 87.5
        assert "id" in data

    def test_list_kpi_metrics(self, client: TestClient, admin_headers):
        client.post("/api/v1/kpi/metrics", headers=admin_headers, json={
            "name": "OTIF",
            "kpi_type": "otif",
            "period": "2026-03-01",
            "actual_value": 95.0,
            "target_value": 98.0,
            "unit": "percent",
        })
        resp = client.get("/api/v1/kpi/metrics", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        items = data.get("items", data) if isinstance(data, dict) else data
        assert len(items) >= 1

    def test_get_kpi_metric_by_id(self, client: TestClient, admin_headers):
        create_resp = client.post("/api/v1/kpi/metrics", headers=admin_headers, json={
            "name": "Inventory Turns",
            "kpi_type": "inventory_turns",
            "period": "2026-03-01",
            "actual_value": 6.2,
            "target_value": 8.0,
            "unit": "turns",
        })
        kpi_id = create_resp.json()["id"]
        resp = client.get(f"/api/v1/kpi/metrics/{kpi_id}", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == kpi_id

    def test_get_nonexistent_kpi_returns_404(self, client: TestClient, admin_headers):
        resp = client.get("/api/v1/kpi/metrics/99999", headers=admin_headers)
        assert resp.status_code == 404

    def test_update_kpi_metric(self, client: TestClient, admin_headers):
        create_resp = client.post("/api/v1/kpi/metrics", headers=admin_headers, json={
            "name": "Service Level",
            "kpi_type": "service_level",
            "period": "2026-03-01",
            "actual_value": 92.0,
            "target_value": 95.0,
            "unit": "percent",
        })
        kpi_id = create_resp.json()["id"]
        resp = client.put(f"/api/v1/kpi/metrics/{kpi_id}", headers=admin_headers, json={
            "actual_value": 93.5,
        })
        assert resp.status_code == 200
        assert float(resp.json()["actual_value"]) == 93.5

    def test_list_kpi_unauthenticated_returns_401(self, client: TestClient):
        resp = client.get("/api/v1/kpi/metrics")
        assert resp.status_code == 401


class TestKPISummary:

    def test_kpi_summary_endpoint(self, client: TestClient, admin_headers):
        resp = client.get("/api/v1/kpi/summary", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, (list, dict))

    def test_kpi_alerts_endpoint(self, client: TestClient, admin_headers):
        # Create a KPI below target to trigger alert
        client.post("/api/v1/kpi/metrics", headers=admin_headers, json={
            "name": "Low Forecast Accuracy",
            "kpi_type": "forecast_accuracy",
            "period": "2026-03-01",
            "actual_value": 60.0,  # well below target
            "target_value": 90.0,
            "unit": "percent",
        })
        resp = client.get("/api/v1/kpi/alerts", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, (list, dict))


class TestKPIFilters:

    def test_filter_by_kpi_type(self, client: TestClient, admin_headers):
        client.post("/api/v1/kpi/metrics", headers=admin_headers, json={
            "name": "OTIF Q1",
            "kpi_type": "otif",
            "period": "2026-01-01",
            "actual_value": 94.0,
            "target_value": 98.0,
            "unit": "percent",
        })
        resp = client.get("/api/v1/kpi/metrics?kpi_type=otif", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        items = data.get("items", data) if isinstance(data, dict) else data
        for item in items:
            assert item["kpi_type"] == "otif"

    def test_filter_by_period(self, client: TestClient, admin_headers):
        client.post("/api/v1/kpi/metrics", headers=admin_headers, json={
            "name": "March KPI",
            "kpi_type": "forecast_accuracy",
            "period": "2026-03-01",
            "actual_value": 88.0,
            "target_value": 90.0,
            "unit": "percent",
        })
        resp = client.get(
            "/api/v1/kpi/metrics?period_start=2026-03-01&period_end=2026-03-31",
            headers=admin_headers,
        )
        assert resp.status_code == 200
