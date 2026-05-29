from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nexus_r.events import Event, PermissionTier


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
def chat_handler():
    from modules.web_ui.src.chat_handler import ChatHandler

    store = FakeEventStore()
    cost_tracker = AsyncMock()
    router = AsyncMock()
    ws_handler = AsyncMock()
    perms = AsyncMock()

    handler = ChatHandler(
        event_store=store,
        cost_tracker=cost_tracker,
        router=router,
        ws_handler=ws_handler,
        perms=perms,
    )
    return handler, store, cost_tracker, router, ws_handler, perms


class TestChatHandlerSendMessage:
    @pytest.mark.asyncio
    async def test_send_message_creates_conversation(self, chat_handler):
        handler, store, _, router, ws_handler, perms = chat_handler
        perms.check.return_value = MagicMock(allowed=True)

        class FakeRoute:
            selected_model = "groq/llama3"
            selected_tier = "T2"
            cost_estimate = 0.001

        router.route.return_value = FakeRoute()
        router.stream = _make_stream(
            {"text": "Hello!", "model_name": "groq/llama3"},
            {"text": " How can I help?", "done": True},
        )

        result = await handler.send_message("Hi there")

        assert result["status"] == "processing"
        assert result["conversation_id"].startswith("conv_")
        assert result["message_id"] is not None

        conv_events = await store.get_by_type("conversation_created")
        assert len(conv_events) == 1
        assert conv_events[0].data["title"] == "Hi there"

        sent_events = await store.get_by_type("chat_message_sent")
        assert len(sent_events) == 1
        assert sent_events[0].data["content"] == "Hi there"

    @pytest.mark.asyncio
    async def test_send_message_uses_existing_conversation(self, chat_handler):
        handler, store, _, router, ws_handler, perms = chat_handler
        perms.check.return_value = MagicMock(allowed=True)

        class FakeRoute:
            selected_model = "groq/llama3"
            selected_tier = "T2"
            cost_estimate = 0.001

        router.route.return_value = FakeRoute()
        router.stream = _make_stream(
            {"text": "Sure!", "done": True},
        )

        conv_id = "conv_existing_123"
        result = await handler.send_message("Another message", conversation_id=conv_id)

        assert result["conversation_id"] == conv_id
        conv_events = await store.get_by_type("conversation_created")
        assert len(conv_events) == 0

    @pytest.mark.asyncio
    async def test_send_message_blocked_by_perms(self, chat_handler):
        handler, store, cost_tracker, router, ws_handler, perms = chat_handler

        class FakeDecision:
            allowed = False

        perms.check.return_value = FakeDecision()

        result = await handler.send_message("Blocked message")

        assert result["blocked"] is True
        assert result["content"] == "Message blocked by trust layer."
        assert result["cost"] == 0.0

        received = await store.get_by_type("chat_message_received")
        assert len(received) == 1
        assert received[0].data["blocked"] is True
        cost_tracker.record.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_no_ws_handler_sync_path(self, chat_handler):
        handler, store, cost_tracker, router, ws_handler, perms = chat_handler
        perms.check.return_value = MagicMock(allowed=True)

        handler.ws_handler = None

        class FakeRoute:
            selected_model = "groq/llama3"
            selected_tier = "T2"
            cost_estimate = 0.001

        router.route.return_value = FakeRoute()
        router.complete.return_value = {
            "text": "Sync response",
            "cost": 0.002,
            "model_name": "groq/llama3",
        }

        result = await handler.send_message("Sync test")

        assert result["role"] == "assistant"
        assert "Sync response" in result["content"]
        assert result["cost"] == 0.002

    @pytest.mark.asyncio
    async def test_stream_error_sends_chat_error(self, chat_handler):
        handler, store, cost_tracker, router, ws_handler, perms = chat_handler
        perms.check.return_value = MagicMock(allowed=True)

        class FakeRoute:
            selected_model = "groq/llama3"
            selected_tier = "T2"
            cost_estimate = 0.001

        router.route.return_value = FakeRoute()

        async def _broken_stream(*args, **kwargs):
            raise RuntimeError("Stream failure")
            yield  # pragma: no cover

        router.stream = _broken_stream

        result = await handler.send_message("Stream error test")
        assert result["status"] == "processing"

        await asyncio.sleep(0.05)
        ws_handler.broadcast.assert_called()
        call_args = ws_handler.broadcast.call_args
        if call_args:
            msg = call_args[0][0]
            if msg["type"] == "chat_error":
                assert "Stream failure" in msg["error"]

    @pytest.mark.asyncio
    async def test_send_message_with_model_override(self, chat_handler):
        handler, store, _, router, ws_handler, perms = chat_handler
        perms.check.return_value = MagicMock(allowed=True)

        class FakeRoute:
            selected_model = "groq/llama3"
            selected_tier = "T2"
            cost_estimate = 0.001

        router.route.return_value = FakeRoute()
        router.stream = _make_stream(
            {"text": "Custom model response", "done": True},
        )

        result = await handler.send_message("Model test", model="local/mock")
        assert result["model"] == "local/mock"

    @pytest.mark.asyncio
    async def test_send_message_broadcasts_conversation_created(self, chat_handler):
        handler, store, _, router, ws_handler, perms = chat_handler
        perms.check.return_value = MagicMock(allowed=True)

        class FakeRoute:
            selected_model = "groq/llama3"
            selected_tier = "T2"
            cost_estimate = 0.001

        router.route.return_value = FakeRoute()
        router.stream = _make_stream(
            {"text": "Welcome!", "done": True},
        )

        await handler.send_message("First message")
        conv_calls = [c for c in ws_handler.broadcast.call_args_list
                      if c[0][0].get("type") == "conversation_created"]
        assert len(conv_calls) == 1


class TestChatHandlerQueries:
    @pytest.mark.asyncio
    async def test_get_conversations_empty(self, chat_handler):
        handler, store, _, _, _, _ = chat_handler
        result = await handler.get_conversations()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_conversations_with_data(self, chat_handler):
        handler, store, _, _, _, _ = chat_handler

        store.events.append(Event(
            event_type="conversation_created",
            data={
                "conversation_id": "conv_001",
                "title": "Test conversation",
                "created_at": "2026-05-25T00:00:00Z",
                "message_count": 0,
            },
        ))
        store.events.append(Event(
            event_type="chat_message_sent",
            data={"conversation_id": "conv_001", "message_id": "msg_001"},
        ))

        result = await handler.get_conversations()
        assert len(result) == 1
        assert result[0]["conversation_id"] == "conv_001"
        assert result[0]["title"] == "Test conversation"

    @pytest.mark.asyncio
    async def test_get_history_empty(self, chat_handler):
        handler, store, _, _, _, _ = chat_handler
        result = await handler.get_history()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_history_with_messages(self, chat_handler):
        handler, store, _, _, _, _ = chat_handler

        store.events.append(Event(
            event_type="chat_message_sent",
            data={
                "message_id": "msg_001",
                "conversation_id": "conv_001",
                "content": "User message",
                "model": "",
                "timestamp": "2026-05-25T00:00:00Z",
            },
        ))
        store.events.append(Event(
            event_type="chat_message_received",
            data={
                "message_id": "msg_001",
                "parent_message_id": "msg_001",
                "conversation_id": "conv_001",
                "content": "Assistant reply",
                "role": "assistant",
                "model": "groq/llama3",
                "cost": 0.001,
                "latency_ms": 150.0,
                "timestamp": "2026-05-25T00:00:01Z",
                "blocked": False,
            },
        ))

        result = await handler.get_history(conversation_id="conv_001")
        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "User message"
        assert result[1]["role"] == "assistant"
        assert result[1]["content"] == "Assistant reply"
        assert result[1]["cost"] == 0.001

    @pytest.mark.asyncio
    async def test_get_history_filters_by_conversation(self, chat_handler):
        handler, store, _, _, _, _ = chat_handler

        store.events.append(Event(
            event_type="chat_message_sent",
            data={
                "message_id": "msg_001",
                "conversation_id": "conv_001",
                "content": "In conv 1",
                "model": "",
                "timestamp": "2026-05-25T00:00:00Z",
            },
        ))
        store.events.append(Event(
            event_type="chat_message_sent",
            data={
                "message_id": "msg_002",
                "conversation_id": "conv_002",
                "content": "In conv 2",
                "model": "",
                "timestamp": "2026-05-25T00:00:01Z",
            },
        ))

        result = await handler.get_history(conversation_id="conv_001")
        assert len(result) == 1
        assert result[0]["content"] == "In conv 1"

    @pytest.mark.asyncio
    async def test_get_message_found(self, chat_handler):
        handler, store, _, _, _, _ = chat_handler

        store.events.append(Event(
            event_type="chat_message_sent",
            data={
                "message_id": "msg_001",
                "conversation_id": "conv_001",
                "content": "Hello!",
                "model": "",
                "timestamp": "2026-05-25T00:00:00Z",
            },
        ))

        result = await handler.get_message("msg_001")
        assert result is not None
        assert result["content"] == "Hello!"
        assert result["role"] == "user"

    @pytest.mark.asyncio
    async def test_get_message_not_found(self, chat_handler):
        handler, store, _, _, _, _ = chat_handler
        result = await handler.get_message("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_message_finds_received(self, chat_handler):
        handler, store, _, _, _, _ = chat_handler

        store.events.append(Event(
            event_type="chat_message_received",
            data={
                "message_id": "msg_002",
                "parent_message_id": "msg_002",
                "conversation_id": "conv_001",
                "content": "Assistant reply",
                "role": "assistant",
                "model": "groq/llama3",
                "cost": 0.001,
                "latency_ms": 100.0,
                "timestamp": "2026-05-25T00:00:01Z",
                "blocked": False,
            },
        ))

        result = await handler.get_message("msg_002")
        assert result is not None
        assert result["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_get_message_count(self, chat_handler):
        handler, store, _, _, _, _ = chat_handler

        store.events.append(Event(
            event_type="chat_message_sent",
            data={"message_id": "msg_001", "conversation_id": "conv_001"},
        ))
        store.events.append(Event(
            event_type="chat_message_sent",
            data={"message_id": "msg_002", "conversation_id": "conv_001"},
        ))
        store.events.append(Event(
            event_type="chat_message_sent",
            data={"message_id": "msg_003", "conversation_id": "conv_002"},
        ))

        count = await handler._get_message_count("conv_001")
        assert count == 2

    @pytest.mark.asyncio
    async def test_get_conversations_pagination(self, chat_handler):
        handler, store, _, _, _, _ = chat_handler

        for i in range(5):
            store.events.append(Event(
                event_type="conversation_created",
                data={
                    "conversation_id": f"conv_{i:03d}",
                    "title": f"Conversation {i}",
                    "created_at": f"2026-05-25T0{i}:00:00Z",
                    "message_count": 0,
                },
            ))

        result = await handler.get_conversations(limit=2, offset=0)
        assert len(result) == 2
        assert result[0]["conversation_id"] == "conv_004"

    @pytest.mark.asyncio
    async def test_get_history_pagination(self, chat_handler):
        handler, store, _, _, _, _ = chat_handler

        for i in range(10):
            store.events.append(Event(
                event_type="chat_message_sent",
                data={
                    "message_id": f"msg_{i:03d}",
                    "conversation_id": "conv_001",
                    "content": f"Message {i}",
                    "model": "",
                    "timestamp": f"2026-05-25T{10+i//60:02d}:{i%60:02d}:00Z",
                },
            ))

        result = await handler.get_history(conversation_id="conv_001", limit=3, offset=0)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_stream_response_logs_cost_and_broadcasts(self, chat_handler):
        handler, store, cost_tracker, router, ws_handler, perms = chat_handler
        perms.check.return_value = MagicMock(allowed=True)

        class FakeRoute:
            selected_model = "groq/llama3"
            selected_tier = "T2"
            cost_estimate = 0.005

        router.route.return_value = FakeRoute()
        router.stream = _make_stream(
            {"text": "Hello", "model_name": "groq/llama3"},
            {"text": " world", "done": True},
        )

        result = await handler.send_message("Stream cost test")
        if handler._active_tasks:
            await asyncio.gather(*handler._active_tasks.values(), return_exceptions=True)

        received = await store.get_by_type("chat_message_received")
        assert len(received) >= 1

        cost_tracker.record.assert_called()
        ws_handler.notify_cost_update.assert_called()
        ws_handler.broadcast.assert_called()


def _make_stream(*items):
    async def stream(*args, **kwargs):
        for item in items:
            yield item
    return stream
