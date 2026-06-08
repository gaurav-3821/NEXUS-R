from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from modules.web_ui.src.app import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestHealthEndpoints:
    def test_health_endpoint_returns_200(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data

    def test_ready_endpoint_returns_200_when_ready(self, client: TestClient) -> None:
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    def test_health_response_has_required_fields(self, client: TestClient) -> None:
        response = client.get("/health")
        data = response.json()
        required_fields = {"status", "version", "timestamp", "uptime"}
        assert required_fields.issubset(data.keys())

    def test_health_returns_json_content_type(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.headers["content-type"] == "application/json"
