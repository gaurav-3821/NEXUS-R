from __future__ import annotations

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from nexus_r.events import Event


@pytest.fixture
def event_store():
    class FakeEventStore:
        def __init__(self) -> None:
            self.events: list[Event] = []
            self._initialized = False

        async def initialize(self) -> None:
            self._initialized = True

        async def append(self, event: Event) -> str:
            self.events.append(event)
            return event.id

        async def get_by_type(self, event_type: str) -> list[Event]:
            return [e for e in self.events if e.event_type == event_type]

    return FakeEventStore()


@pytest.fixture
def client(event_store):
    os.environ["NEXUS_DASHBOARD_TOKEN"] = "test-token-123"
    from modules.web_ui.src.app import create_app

    # Create app which instantiates ModelManager
    app = create_app(event_store)
    client = TestClient(app)
    yield client
    os.environ.pop("NEXUS_DASHBOARD_TOKEN", None)


class TestModelsAPI:
    def test_status_no_auth(self, client):
        resp = client.get("/api/v1/models/status")
        assert resp.status_code == 401

    def test_status_invalid_token(self, client):
        resp = client.get("/api/v1/models/status?token=wrong")
        assert resp.status_code == 403

    def test_get_status(self, client):
        with patch("modules.cognition_router.src.model_manager.ModelManager.load_saved_config") as mock_load:
            mock_load.return_value = {
                "local_model": "ollama/gemma2:9b",
                "cloud_provider": "openai",
                "api_key": "sk-12345"
            }
            resp = client.get("/api/v1/models/status?token=test-token-123")
            assert resp.status_code == 200
            data = resp.json()
            assert "current" in data
            assert data["current"]["local_model"] == "ollama/gemma2:9b"
            assert data["current"]["cloud_provider"] == "openai"
            assert data["current"]["api_key_configured"] is True
            assert "cloud_options" in data

    def test_list_local(self, client):
        with patch("modules.cognition_router.src.model_manager.ModelManager.list_all_local_models", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = {
                "ollama": [{"name": "gemma2:9b", "size": "5.5GB", "source": "ollama"}],
                "lmstudio": [],
                "all": [{"name": "gemma2:9b", "size": "5.5GB", "source": "ollama"}]
            }
            resp = client.get("/api/v1/models/list-local?token=test-token-123")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["ollama"]) == 1
            assert data["ollama"][0]["name"] == "gemma2:9b"

    def test_download_jobs(self, client):
        with patch("modules.cognition_router.src.model_manager.ModelManager.get_active_jobs") as mock_jobs:
            mock_jobs.return_value = [
                {"job_id": "job1", "model_name": "qwen2.5:7b", "status": "downloading", "progress": 45}
            ]
            resp = client.get("/api/v1/models/download-jobs?token=test-token-123")
            assert resp.status_code == 200
            data = resp.json()
            assert "jobs" in data
            assert len(data["jobs"]) == 1
            assert data["jobs"][0]["job_id"] == "job1"

    def test_download_status_found(self, client):
        with patch("modules.cognition_router.src.model_manager.ModelManager.get_download_status") as mock_status:
            mock_status.return_value = {
                "job_id": "job1", "model_name": "qwen2.5:7b", "status": "downloading", "progress": 45
            }
            resp = client.get("/api/v1/models/download-status/job1?token=test-token-123")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "downloading"

    def test_download_status_not_found(self, client):
        with patch("modules.cognition_router.src.model_manager.ModelManager.get_download_status") as mock_status:
            mock_status.return_value = None
            resp = client.get("/api/v1/models/download-status/nonexistent?token=test-token-123")
            assert resp.status_code == 404

    def test_ollama_status(self, client):
        with patch("modules.cognition_router.src.model_manager.ModelManager.check_model_status", new_callable=AsyncMock) as mock_status:
            mock_status.return_value = {"installed": True, "model": "gemma2:9b", "size": "5.5GB"}
            resp = client.get("/api/v1/models/ollama-status/gemma2:9b?token=test-token-123")
            assert resp.status_code == 200
            data = resp.json()
            assert data["installed"] is True
            assert data["size"] == "5.5GB"

    def test_post_download(self, client):
        with patch("modules.cognition_router.src.model_manager.ModelManager.start_download") as mock_start:
            mock_start.return_value = {"success": True, "job_id": "job-123", "model": "gemma2:9b"}
            resp = client.post("/api/v1/models/download?token=test-token-123", json={"model_name": "gemma2:9b"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["job_id"] == "job-123"

    def test_post_download_cancel(self, client):
        with patch("modules.cognition_router.src.model_manager.ModelManager.cancel_download") as mock_cancel:
            mock_cancel.return_value = {"success": True}
            resp = client.post("/api/v1/models/download-cancel/job-123?token=test-token-123")
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True

    def test_post_test_local(self, client):
        with patch("modules.cognition_router.src.model_manager.ModelManager.test_local_model", new_callable=AsyncMock) as mock_test:
            mock_test.return_value = {"success": True, "latency_ms": 120.5, "response": "hello"}
            resp = client.post("/api/v1/models/test?token=test-token-123", json={"local_model": "ollama/gemma2:9b"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["latency_ms"] == 120.5

    def test_post_test_cloud(self, client):
        with patch("modules.cognition_router.src.model_manager.ModelManager.test_cloud_connection", new_callable=AsyncMock) as mock_test:
            mock_test.return_value = {"success": True, "latency_ms": 250.0, "response": "hi"}
            resp = client.post("/api/v1/models/test?token=test-token-123", json={"cloud_provider": "groq", "api_key": "gsk-123"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["latency_ms"] == 250.0

    def test_post_configure(self, client):
        with patch("modules.cognition_router.src.model_manager.ModelManager.configure", new_callable=AsyncMock) as mock_config:
            mock_config.return_value = {"status": "ok", "local_model": "ollama/gemma2:9b", "cloud_provider": "none"}
            resp = client.post("/api/v1/models/configure?token=test-token-123", json={
                "local_model": "ollama/gemma2:9b",
                "cloud_provider": "none"
            })
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"
