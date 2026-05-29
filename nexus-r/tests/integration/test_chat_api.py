from __future__ import annotations

import json
import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from nexus_r.events import Event, PermissionTier


def _make_stream(*items):
    async def stream(*args, **kwargs):
        for item in items:
            yield item
    return stream


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


@pytest.fixture
def event_store():
    return FakeEventStore()


@pytest.fixture
def router_mock():
    r = AsyncMock()

    class FakeRoute:
        selected_model = "groq/llama3"
        selected_tier = "T2"
        cost_estimate = 0.001

    r.route.return_value = FakeRoute()
    r.stream = _make_stream(
        {"text": "Hello!", "model_name": "groq/llama3"},
        {"text": " This is a test response.", "done": True},
    )
    r.complete.return_value = {"text": "Sync response", "cost": 0.002, "model_name": "groq/llama3"}
    return r


@pytest.fixture
def chat_handler(event_store, router_mock):
    from modules.web_ui.src.chat_handler import ChatHandler

    cost_tracker = AsyncMock()
    ws_handler = None
    perms = AsyncMock()
    perms.check.return_value = MagicMock(allowed=True)

    handler = ChatHandler(
        event_store=event_store,
        cost_tracker=cost_tracker,
        router=router_mock,
        ws_handler=ws_handler,
        perms=perms,
    )
    return handler


@pytest.fixture
def client(event_store, chat_handler):
    os.environ["NEXUS_DASHBOARD_TOKEN"] = "chat-test-token"
    from modules.web_ui.src.app import create_app, _rate_limiter

    _rate_limiter.clear()
    app = create_app(event_store, chat_handler=chat_handler)
    yield TestClient(app)
    os.environ.pop("NEXUS_DASHBOARD_TOKEN", None)


class TestChatAPI:
    def test_chat_send_no_auth(self, client):
        resp = client.post("/api/v1/chat?message=hello")
        assert resp.status_code == 401

    def test_chat_send_with_auth(self, client):
        resp = client.post("/api/v1/chat?token=chat-test-token&message=Hello+world")
        assert resp.status_code == 200
        data = resp.json()
        assert "message_id" in data
        assert "conversation_id" in data
        assert data["role"] == "assistant"
        assert "content" in data

    def test_chat_send_empty_message_rejected(self, client):
        resp = client.post("/api/v1/chat?token=chat-test-token&message=")
        assert resp.status_code == 422

    def test_chat_send_with_conversation_id(self, client, event_store):
        resp = client.post(
            "/api/v1/chat?token=chat-test-token&message=First&conversation_id=conv_001"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["conversation_id"] == "conv_001"

    def test_chat_conversations_no_auth(self, client):
        resp = client.get("/api/v1/chat/conversations")
        assert resp.status_code == 401

    def test_chat_conversations_empty(self, client):
        resp = client.get("/api/v1/chat/conversations?token=chat-test-token")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_chat_conversations_with_data(self, client, event_store):
        event_store.events.append(Event(
            event_type="conversation_created",
            data={
                "conversation_id": "conv_001",
                "title": "Test conversation",
                "created_at": "2026-05-25T00:00:00Z",
                "message_count": 0,
            },
        ))
        resp = client.get("/api/v1/chat/conversations?token=chat-test-token")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["conversation_id"] == "conv_001"

    def test_chat_history_no_auth(self, client):
        resp = client.get("/api/v1/chat/history")
        assert resp.status_code == 401

    def test_chat_history_empty(self, client):
        resp = client.get("/api/v1/chat/history?token=chat-test-token")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_chat_history_with_messages(self, client, event_store):
        event_store.events.append(Event(
            event_type="chat_message_sent",
            data={
                "message_id": "msg_001", "conversation_id": "conv_001",
                "content": "User query", "model": "",
                "timestamp": "2026-05-25T00:00:00Z",
            },
        ))
        event_store.events.append(Event(
            event_type="chat_message_received",
            data={
                "message_id": "msg_001", "parent_message_id": "msg_001",
                "conversation_id": "conv_001", "content": "Assistant reply",
                "role": "assistant", "model": "groq/llama3",
                "cost": 0.001, "latency_ms": 100.0,
                "timestamp": "2026-05-25T00:00:01Z", "blocked": False,
            },
        ))
        resp = client.get("/api/v1/chat/history?token=chat-test-token")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_chat_history_filter_by_conversation(self, client, event_store):
        event_store.events.append(Event(
            event_type="chat_message_sent",
            data={
                "message_id": "msg_001", "conversation_id": "conv_001",
                "content": "In conv 1", "model": "",
                "timestamp": "2026-05-25T00:00:00Z",
            },
        ))
        event_store.events.append(Event(
            event_type="chat_message_sent",
            data={
                "message_id": "msg_002", "conversation_id": "conv_002",
                "content": "In conv 2", "model": "",
                "timestamp": "2026-05-25T00:00:01Z",
            },
        ))
        resp = client.get(
            "/api/v1/chat/history?token=chat-test-token&conversation_id=conv_001"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["content"] == "In conv 1"

    def test_chat_get_message_found(self, client, event_store):
        event_store.events.append(Event(
            event_type="chat_message_sent",
            data={
                "message_id": "msg_001", "conversation_id": "conv_001",
                "content": "Found message", "model": "",
                "timestamp": "2026-05-25T00:00:00Z",
            },
        ))
        resp = client.get("/api/v1/chat/message/msg_001?token=chat-test-token")
        assert resp.status_code == 200
        assert resp.json()["content"] == "Found message"

    def test_chat_get_message_not_found(self, client):
        resp = client.get("/api/v1/chat/message/nonexistent?token=chat-test-token")
        assert resp.status_code == 404

    def test_chat_send_creates_conversation_event(self, client, event_store):
        resp = client.post("/api/v1/chat?token=chat-test-token&message=New+conversation")
        assert resp.status_code == 200
        data = resp.json()
        assert "message_id" in data
        assert "conversation_id" in data
        conv_events = [e for e in event_store.events if e.event_type == "conversation_created"]
        assert len(conv_events) == 1
        sent_events = [e for e in event_store.events if e.event_type == "chat_message_sent"]
        assert len(sent_events) == 1

    def test_chat_conversations_pagination(self, client, event_store):
        for i in range(5):
            event_store.events.append(Event(
                event_type="conversation_created",
                data={
                    "conversation_id": f"conv_{i:03d}",
                    "title": f"Conv {i}",
                    "created_at": f"2026-05-25T0{i}:00:00Z",
                    "message_count": 0,
                },
            ))
        resp = client.get("/api/v1/chat/conversations?token=chat-test-token&limit=2&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_chat_history_pagination(self, client, event_store):
        for i in range(10):
            event_store.events.append(Event(
                event_type="chat_message_sent",
                data={
                    "message_id": f"msg_{i:03d}",
                    "conversation_id": "conv_001",
                    "content": f"Msg {i}",
                    "model": "",
                    "timestamp": f"2026-05-25T{10+i//60:02d}:{i%60:02d}:00Z",
                },
            ))
        resp = client.get(
            "/api/v1/chat/history?token=chat-test-token&conversation_id=conv_001&limit=3&offset=0"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
