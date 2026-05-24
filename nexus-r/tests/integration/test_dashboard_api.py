from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

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
    os.environ["NEXUS_DASHBOARD_TOKEN"] = "test-token-123"
    from modules.web_ui.src.app import create_app

    app = create_app(event_store)
    client = TestClient(app)
    yield client
    os.environ.pop("NEXUS_DASHBOARD_TOKEN", None)


def _populate_cost_events(store, count: int = 10, task_prefix: str = "task"):
    for i in range(count):
        store.events.append(Event(
            event_type="cost_recorded",
            data={
                "task_id": f"{task_prefix}_{i:03d}",
                "amount": 0.01 * (i + 1),
                "model": "groq/llama3" if i % 2 == 0 else "local/mock",
                "tier": f"T{i % 4 + 1}",
                "timestamp": f"2026-05-24T{10 + i:02d}:{i % 60:02d}:00Z",
                "action_type": "general_llm",
            },
        ))


class TestDashboardAPI:
    def test_get_summary_no_auth(self, client):
        resp = client.get("/api/v1/cost/summary")
        assert resp.status_code == 401

    def test_get_summary_invalid_token(self, client):
        resp = client.get("/api/v1/cost/summary?token=wrong")
        assert resp.status_code == 403

    def test_get_summary_empty(self, client):
        resp = client.get("/api/v1/cost/summary?token=test-token-123")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_cost"] == 0.0
        assert data["per_tier"] == {}
        assert data["per_model"] == {}
        assert data["task_count"] == 0

    def test_get_summary_with_data(self, client, event_store):
        _populate_cost_events(event_store, 10)
        resp = client.get("/api/v1/cost/summary?token=test-token-123")
        assert resp.status_code == 200
        data = resp.json()
        expected_total = sum(0.01 * (i + 1) for i in range(10))
        assert data["total_cost"] == round(expected_total, 6)
        assert len(data["per_tier"]) == 4
        assert len(data["per_model"]) == 2
        assert data["task_count"] == 10

    def test_get_tasks_paginated(self, client, event_store):
        _populate_cost_events(event_store, 20)
        resp = client.get("/api/v1/cost/tasks?token=test-token-123&limit=5&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 5
        timestamps = [t["timestamp"] for t in data]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_get_tasks_page_two(self, client, event_store):
        _populate_cost_events(event_store, 20)
        resp = client.get("/api/v1/cost/tasks?token=test-token-123&limit=5&offset=5")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 5

    def test_get_tasks_filter_by_tier(self, client, event_store):
        _populate_cost_events(event_store, 20)
        resp = client.get("/api/v1/cost/tasks?token=test-token-123&tier=T1")
        assert resp.status_code == 200
        data = resp.json()
        for t in data:
            assert t["tier"] == "T1"

    def test_get_tasks_filter_by_model(self, client, event_store):
        _populate_cost_events(event_store, 20)
        resp = client.get("/api/v1/cost/tasks?token=test-token-123&model=groq/llama3")
        assert resp.status_code == 200
        data = resp.json()
        for t in data:
            assert t["model"] == "groq/llama3"

    def test_get_task_detail_found(self, client, event_store):
        _populate_cost_events(event_store, 5)
        resp = client.get("/api/v1/cost/task/task_001?token=test-token-123")
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == "task_001"

    def test_get_task_detail_not_found(self, client):
        resp = client.get("/api/v1/cost/task/nonexistent?token=test-token-123")
        assert resp.status_code == 404
        assert "CD-002" in resp.json()["detail"]

    def test_get_session_found(self, client, event_store):
        for i in range(3):
            event_store.events.append(Event(
                event_type="cost_recorded",
                data={
                    "task_id": f"ses_abc_task_{i}",
                    "amount": 0.01,
                    "model": "groq/llama3",
                    "tier": "T1",
                    "timestamp": f"2026-05-24T1{i}:00:00Z",
                },
            ))
        resp = client.get("/api/v1/cost/session/ses_abc?token=test-token-123")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == "ses_abc"
        assert data["task_count"] == 3

    def test_get_session_not_found(self, client):
        resp = client.get("/api/v1/cost/session/nosession?token=test-token-123")
        assert resp.status_code == 404
        assert "CD-003" in resp.json()["detail"]

    def test_get_tiers(self, client, event_store):
        _populate_cost_events(event_store, 8)
        resp = client.get("/api/v1/cost/tiers?token=test-token-123")
        assert resp.status_code == 200

    def test_get_models(self, client, event_store):
        _populate_cost_events(event_store, 8)
        resp = client.get("/api/v1/cost/models?token=test-token-123")
        assert resp.status_code == 200

    def test_get_etd(self, client):
        resp = client.get("/api/v1/etd?token=test-token-123")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_audit_log(self, client, event_store):
        _populate_cost_events(event_store, 10)
        resp = client.get("/api/v1/audit/log?token=test-token-123&limit=5&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) <= 5

    def test_get_audit_log_task_id_filter(self, client, event_store):
        _populate_cost_events(event_store, 10)
        resp = client.get("/api/v1/audit/log?token=test-token-123&task_id=task_001")
        assert resp.status_code == 200
        data = resp.json()
        for r in data:
            assert r["task_id"] == "task_001"

    def test_get_audit_log_model_filter(self, client, event_store):
        _populate_cost_events(event_store, 10)
        resp = client.get("/api/v1/audit/log?token=test-token-123&model=groq/llama3")
        assert resp.status_code == 200
        data = resp.json()
        for r in data:
            assert r["model"] == "groq/llama3"

    def test_get_audit_log_date_range(self, client, event_store):
        event_store.events.append(Event(
            event_type="cost_recorded",
            data={
                "task_id": "task_early", "amount": 0.01, "model": "m1", "tier": "T1",
                "timestamp": "2026-05-01T00:00:00Z",
            },
        ))
        event_store.events.append(Event(
            event_type="cost_recorded",
            data={
                "task_id": "task_late", "amount": 0.02, "model": "m2", "tier": "T1",
                "timestamp": "2026-05-30T00:00:00Z",
            },
        ))
        resp = client.get("/api/v1/audit/log?token=test-token-123&start_date=2026-05-15T00:00:00Z")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["task_id"] == "task_late"

    def test_get_audit_log_cost_range(self, client, event_store):
        _populate_cost_events(event_store, 5)
        resp = client.get("/api/v1/audit/log?token=test-token-123&cost_min=0.04&cost_max=0.05")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_get_tasks_with_date_filters(self, client, event_store):
        event_store.events.append(Event(
            event_type="cost_recorded",
            data={
                "task_id": "task_early", "amount": 0.01, "model": "m1", "tier": "T1",
                "timestamp": "2026-05-01T00:00:00Z",
            },
        ))
        event_store.events.append(Event(
            event_type="cost_recorded",
            data={
                "task_id": "task_late", "amount": 0.02, "model": "m2", "tier": "T1",
                "timestamp": "2026-05-30T00:00:00Z",
            },
        ))
        resp = client.get("/api/v1/cost/tasks?token=test-token-123&start_date=2026-05-15T00:00:00Z")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["task_id"] == "task_late"

    def test_rate_limit_returns_429(self, client):
        from modules.web_ui.src.app import _rate_limiter
        _rate_limiter.clear()
        for _ in range(100):
            resp = client.get(f"/api/v1/cost/summary?token=test-token-123")
            assert resp.status_code == 200
        resp = client.get("/api/v1/cost/summary?token=test-token-123")
        assert resp.status_code == 429

    def test_root_returns_html(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_dashboard_html_no_auth(self, client):
        resp = client.get("/api/v1/dashboard")
        assert resp.status_code == 401

    def test_dashboard_html_with_auth(self, client):
        resp = client.get("/api/v1/dashboard?token=test-token-123")
        assert resp.status_code == 200

    def test_etd_with_store(self, event_store):
        from modules.workflow_engine.src.store import ETDStore, IndexedETDEntry
        from modules.workflow_engine.src.parameterizer import ETDEntry

        store = ETDStore()
        entry = ETDEntry(
            id="etd_test",
            intent_signature="test-workflow",
            intent_embedding=[0.1] * 128,
            input_schema={},
            output_schema={},
            tool_sequence=[],
            parameter_slots=[],
            invariant_checks=[],
            success_count=10,
            failure_count=2,
            generalization_success_rate=0.833,
            last_validated="2026-05-24T00:00:00Z",
            avg_cost=0.012,
            avg_latency_ms=500.0,
        )
        indexed = IndexedETDEntry(
            entry=entry,
            hit_count=5,
            created_at="2026-05-24T00:00:00Z",
        )
        store.add(indexed)

        orig_token = os.environ.get("NEXUS_DASHBOARD_TOKEN", "")
        os.environ["NEXUS_DASHBOARD_TOKEN"] = "test-token-etd"
        from modules.web_ui.src.app import create_app
        app = create_app(event_store, store)
        c = TestClient(app)
        resp = c.get("/api/v1/etd?token=test-token-etd")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == "etd_test"
        assert data[0]["hit_rate"] == round(5 / 17, 4)
        os.environ["NEXUS_DASHBOARD_TOKEN"] = orig_token


class TestDashboardWebSocket:
    @pytest.mark.asyncio
    async def test_websocket_live_updates(self, event_store):
        os.environ["NEXUS_DASHBOARD_TOKEN"] = "ws-test-token"
        from modules.web_ui.src.app import create_app, get_ws_handler

        app = create_app(event_store)
        ws_handler = get_ws_handler()
        assert ws_handler is not None

        from fastapi.testclient import TestClient
        client = TestClient(app)

        with client.websocket_connect("/ws/v1/cost/live") as ws:
            ws.send_text(json.dumps({"type": "subscribe", "filter": "all"}))
            import asyncio
            await ws_handler.notify_cost_update("live_task_001", 0.05, "groq/llama3", "T1")
            resp = ws.receive_json()
            assert resp["type"] == "cost_update"
            assert resp["task_id"] == "live_task_001"
            assert resp["cost"] == 0.05

        os.environ["NEXUS_DASHBOARD_TOKEN"] = "test-token-123"

    @pytest.mark.asyncio
    async def test_websocket_task_started_notification(self, event_store):
        os.environ["NEXUS_DASHBOARD_TOKEN"] = "ws-test-token-2"
        from modules.web_ui.src.app import create_app, get_ws_handler

        app = create_app(event_store)
        ws_handler = get_ws_handler()

        from fastapi.testclient import TestClient
        client = TestClient(app)

        with client.websocket_connect("/ws/v1/cost/live") as ws:
            ws.send_text(json.dumps({"type": "subscribe", "filter": "all"}))
            import asyncio
            await ws_handler.notify_task_started("live_task_002", 0.01)
            resp = ws.receive_json()
            assert resp["type"] == "task_started"
            assert resp["task_id"] == "live_task_002"

        os.environ["NEXUS_DASHBOARD_TOKEN"] = "test-token-123"

    @pytest.mark.asyncio
    async def test_websocket_task_completed_notification(self, event_store):
        os.environ["NEXUS_DASHBOARD_TOKEN"] = "ws-test-token-3"
        from modules.web_ui.src.app import create_app, get_ws_handler

        app = create_app(event_store)
        ws_handler = get_ws_handler()

        from fastapi.testclient import TestClient
        client = TestClient(app)

        with client.websocket_connect("/ws/v1/cost/live") as ws:
            ws.send_text(json.dumps({"type": "subscribe", "filter": "all"}))
            import asyncio
            await ws_handler.notify_task_completed("live_task_003", 0.03, 200.0)
            resp = ws.receive_json()
            assert resp["type"] == "task_completed"
            assert resp["task_id"] == "live_task_003"
            assert resp["final_cost"] == 0.03

        os.environ["NEXUS_DASHBOARD_TOKEN"] = "test-token-123"

    @pytest.mark.asyncio
    async def test_websocket_session_reset(self, event_store):
        os.environ["NEXUS_DASHBOARD_TOKEN"] = "ws-test-token-4"
        from modules.web_ui.src.app import create_app, get_ws_handler

        app = create_app(event_store)
        ws_handler = get_ws_handler()

        from fastapi.testclient import TestClient
        client = TestClient(app)

        with client.websocket_connect("/ws/v1/cost/live") as ws:
            ws.send_text(json.dumps({"type": "subscribe", "filter": "all"}))
            import asyncio
            await ws_handler.reset()
            resp = ws.receive_json()
            assert resp["type"] == "session_reset"
            assert resp["total_cost"] == 0.0

        os.environ["NEXUS_DASHBOARD_TOKEN"] = "test-token-123"
