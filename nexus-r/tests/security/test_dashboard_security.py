from __future__ import annotations

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from nexus_r.events import Event, PermissionTier


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
    os.environ["NEXUS_DASHBOARD_TOKEN"] = "secure-token-789"
    from modules.web_ui.src.app import create_app, _rate_limiter

    _rate_limiter.clear()
    app = create_app(event_store)
    yield TestClient(app)
    os.environ.pop("NEXUS_DASHBOARD_TOKEN", None)


class TestDashboardAuthentication:
    def test_no_token_returns_401(self, client):
        resp = client.get("/api/v1/cost/summary")
        assert resp.status_code == 401
        assert "Authentication required" in resp.json()["detail"]

    def test_wrong_token_returns_403(self, client):
        resp = client.get("/api/v1/cost/summary?token=wrong-token")
        assert resp.status_code == 403
        assert "Invalid authentication token" in resp.json()["detail"]

    def test_valid_token_returns_200(self, client, event_store):
        event_store.events.append(Event(
            event_type="cost_recorded",
            data={
                "task_id": "task_001",
                "amount": 0.01,
                "model": "groq/llama3",
                "tier": "T1",
                "timestamp": "2026-05-24T10:00:00Z",
            },
        ))
        resp = client.get("/api/v1/cost/summary?token=secure-token-789")
        assert resp.status_code == 200
        assert resp.json()["total_cost"] == 0.01

    def test_all_endpoints_require_auth(self, client):
        endpoints = [
            "/api/v1/cost/summary",
            "/api/v1/cost/tasks",
            "/api/v1/cost/tiers",
            "/api/v1/cost/models",
            "/api/v1/etd",
            "/api/v1/audit/log",
            "/api/v1/dashboard",
        ]
        for ep in endpoints:
            resp = client.get(ep)
            assert resp.status_code == 401, f"{ep} should require auth, got {resp.status_code}"

    def test_expensive_endpoints_require_auth(self, client):
        endpoints = [
            "/api/v1/cost/task/task_001",
            "/api/v1/cost/session/ses_001",
        ]
        for ep in endpoints:
            resp = client.get(ep)
            assert resp.status_code == 401, f"{ep} should require auth, got {resp.status_code}"

    def test_root_endpoint_no_auth(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_static_files_no_auth(self, client):
        resp = client.get("/static/style.css")
        assert resp.status_code == 200

    def test_api_docs_no_auth(self, client):
        resp = client.get("/docs")
        assert resp.status_code == 200

    def test_token_cannot_access_other_tokens_data(self, client, event_store):
        event_store.events.append(Event(
            event_type="cost_recorded",
            data={
                "task_id": "secret_task",
                "amount": 100.0,
                "model": "groq/llama3",
                "tier": "T1",
                "timestamp": "2026-05-24T10:00:00Z",
            },
        ))
        resp = client.get("/api/v1/cost/summary?token=wrong-token")
        assert resp.status_code == 403

    def test_websocket_requires_no_token(self, client):
        with client.websocket_connect("/ws/v1/cost/live") as ws:
            ws.send_text(json.dumps({"type": "subscribe", "filter": "all"}))
            resp = ws.receive_json()
            assert resp is not None

    def test_invalid_websocket_filter_rejected(self, client):
        with client.websocket_connect("/ws/v1/cost/live") as ws:
            ws.send_text(json.dumps({"type": "subscribe", "filter": "invalid:xyz"}))
            resp = ws.receive_json()
            assert "error" in resp
            assert resp["error"] == "CD-006"

    def test_no_cost_data_exposure_without_auth(self, client, event_store):
        event_store.events.append(Event(
            event_type="cost_recorded",
            data={
                "task_id": "sensitive_task",
                "amount": 999.99,
                "model": "groq/llama3",
                "tier": "T4",
                "timestamp": "2026-05-24T10:00:00Z",
            },
        ))
        no_auth_resp = client.get("/api/v1/cost/summary")
        assert no_auth_resp.status_code == 401
        auth_resp = client.get("/api/v1/cost/summary?token=secure-token-789")
        assert auth_resp.status_code == 200
        assert auth_resp.json()["total_cost"] == 999.99


class TestDashboardRateLimiting:
    def test_rate_limit_exceeded(self, client):
        from modules.web_ui.src.app import _rate_limiter
        _rate_limiter.clear()
        for _ in range(100):
            resp = client.get(f"/api/v1/cost/summary?token=secure-token-789")
        resp = client.get("/api/v1/cost/summary?token=secure-token-789")
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers

    def test_rate_limit_per_endpoint(self, client):
        from modules.web_ui.src.app import _rate_limiter
        _rate_limiter.clear()
        for _ in range(100):
            resp = client.get(f"/api/v1/cost/summary?token=secure-token-789")
        tasks_resp = client.get("/api/v1/cost/tasks?token=secure-token-789")
        assert tasks_resp.status_code == 200


class TestDashboardInputValidation:
    def test_invalid_limit_rejected(self, client):
        resp = client.get("/api/v1/cost/tasks?token=secure-token-789&limit=500")
        assert resp.status_code == 422

    def test_negative_offset_rejected(self, client):
        resp = client.get("/api/v1/cost/tasks?token=secure-token-789&offset=-1")
        assert resp.status_code == 422

    def test_special_chars_in_task_id_no_sql_injection(self, client):
        resp = client.get('/api/v1/cost/task/"; DROP TABLE events;--?token=secure-token-789')
        assert resp.status_code == 404

    def test_special_chars_in_session_id_no_crash(self, client):
        resp = client.get("/api/v1/cost/session/../../../etc/passwd?token=secure-token-789")
        assert resp.status_code == 404

    def test_large_payload_no_crash(self, client, event_store):
        for i in range(500):
            event_store.events.append(Event(
                event_type="cost_recorded",
                data={
                    "task_id": f"task_{i}",
                    "amount": 0.01,
                    "model": "groq/llama3",
                    "tier": "T1",
                    "timestamp": "2026-05-24T10:00:00Z",
                },
            ))
        resp = client.get("/api/v1/cost/summary?token=secure-token-789")
        assert resp.status_code == 200
        assert resp.json()["total_cost"] == 5.0


class TestDashboardEdgeCases:
    def test_dashboard_service_unavailable_returns_500(self, event_store):
        os.environ["NEXUS_DASHBOARD_TOKEN"] = "edge-test-token"
        import modules.web_ui.src.app as app_module
        app = app_module.create_app(event_store)
        saved = app_module._dashboard_service
        app_module._dashboard_service = None
        from fastapi.testclient import TestClient
        c = TestClient(app)
        resp = c.get("/api/v1/cost/summary?token=edge-test-token")
        assert resp.status_code == 500
        assert "CD-001" in resp.json()["detail"]
        app_module._dashboard_service = saved
        os.environ.pop("NEXUS_DASHBOARD_TOKEN", None)

    def test_cost_dashboard_error_returns_400(self, event_store):
        os.environ["NEXUS_DASHBOARD_TOKEN"] = "error-test-token"
        from unittest.mock import AsyncMock, patch
        import modules.web_ui.src.app as app_module
        app = app_module.create_app(event_store)
        from fastapi.testclient import TestClient
        c = TestClient(app)
        orig = app_module._dashboard_service.get_summary
        app_module._dashboard_service.get_summary = AsyncMock(
            side_effect=app_module.CostDashboardError("CD-007", "Query too broad")
        )
        resp = c.get("/api/v1/cost/summary?token=error-test-token")
        assert resp.status_code == 400
        assert "CD-007" in resp.json()["detail"]
        app_module._dashboard_service.get_summary = orig
        os.environ.pop("NEXUS_DASHBOARD_TOKEN", None)

    def test_websocket_handler_unavailable(self, event_store):
        os.environ["NEXUS_DASHBOARD_TOKEN"] = "ws-edge-token"
        import modules.web_ui.src.app as app_module
        app = app_module.create_app(event_store)
        saved = app_module._ws_handler
        app_module._ws_handler = None
        from fastapi.testclient import TestClient
        import starlette.websockets
        c = TestClient(app)
        with pytest.raises(starlette.websockets.WebSocketDisconnect):
            with c.websocket_connect("/ws/v1/cost/live"):
                pass
        app_module._ws_handler = saved
        os.environ.pop("NEXUS_DASHBOARD_TOKEN", None)


class TestDashboardChatSecurity:
    def test_chat_endpoints_require_auth(self, client):
        endpoints = [
            ("POST", "/api/v1/chat?message=hello"),
            ("GET", "/api/v1/chat/conversations"),
            ("GET", "/api/v1/chat/history"),
            ("GET", "/api/v1/chat/message/msg_001"),
        ]
        for method, url in endpoints:
            if method == "POST":
                resp = client.post(url)
            else:
                resp = client.get(url)
            assert resp.status_code == 401, f"{method} {url} should require auth, got {resp.status_code}"

    def test_chat_handler_unavailable_returns_501(self, client):
        resp = client.post("/api/v1/chat?token=secure-token-789&message=test")
        assert resp.status_code == 501
        assert "Chat handler not available" in resp.json()["detail"]

    def test_chat_handler_unavailable_returns_501_get(self, client):
        resp = client.get("/api/v1/chat/conversations?token=secure-token-789")
        assert resp.status_code == 501

    def test_chat_handler_unavailable_returns_501_history(self, client):
        resp = client.get("/api/v1/chat/history?token=secure-token-789")
        assert resp.status_code == 501

    def test_chat_handler_unavailable_returns_501_message(self, client):
        resp = client.get("/api/v1/chat/message/msg_001?token=secure-token-789")
        assert resp.status_code == 501

    def test_chat_send_empty_message_rejected_422(self, client):
        resp = client.post("/api/v1/chat?token=secure-token-789&message=")
        assert resp.status_code == 422

    def test_chat_send_message_too_long_rejected_422(self, client):
        long_msg = "x" * 10001
        resp = client.post(f"/api/v1/chat?token=secure-token-789&message={long_msg}")
        assert resp.status_code == 422

    def test_chat_wrong_token_returns_403(self, client):
        resp = client.post("/api/v1/chat?token=wrong-token&message=test")
        assert resp.status_code == 403


class TestDashboardEventSourcing:
    def test_all_dashboard_actions_logged(self, client, event_store):
        ct = None
        from modules.trust_layer.src.cost_tracker import CostTracker
        ct = CostTracker(event_store)
        import asyncio
        asyncio.run(ct.record("audit_task", 0.05, "groq/llama3", PermissionTier.T2))
        events = event_store.events
        cost_events = [e for e in events if e.event_type == "cost_recorded"]
        assert len(cost_events) >= 1

    def test_audit_log_contains_all_cost_events(self, client, event_store):
        import asyncio
        from modules.trust_layer.src.cost_tracker import CostTracker
        ct = CostTracker(event_store)
        for i in range(5):
            asyncio.run(ct.record(f"task_{i}", 0.01 * (i + 1), "groq/llama3", PermissionTier.T1))
        resp = client.get("/api/v1/audit/log?token=secure-token-789&limit=10&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 5
        total = sum(r["cost"] for r in data)
        assert total == round(0.01 + 0.02 + 0.03 + 0.04 + 0.05, 6)
