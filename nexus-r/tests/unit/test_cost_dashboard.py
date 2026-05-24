from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nexus_r.events import Event, PermissionTier
from modules.trust_layer.src.cost_tracker import CostTracker


@dataclass
class FakeETDEntry:
    id: str = ""
    intent_signature: str = ""
    intent_embedding: list[float] = field(default_factory=list)
    input_schema: dict[str, str] = field(default_factory=dict)
    output_schema: dict[str, str] = field(default_factory=dict)
    tool_sequence: list = field(default_factory=list)
    parameter_slots: list[str] = field(default_factory=list)
    invariant_checks: list[str] = field(default_factory=list)
    success_count: int = 0
    failure_count: int = 0
    generalization_success_rate: float = 0.0
    last_validated: str = ""
    avg_cost: float = 0.0
    avg_latency_ms: float = 0.0


@dataclass
class FakeIndexedETDEntry:
    entry: FakeETDEntry = field(default_factory=FakeETDEntry)
    hit_count: int = 0
    created_at: str = ""
    invalidated: bool = False


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


class TestTokenGeneration:
    def test_get_token_uses_env_var(self) -> None:
        from modules.web_ui.src.app import _get_token, _GENERATED_TOKEN

        import os
        orig = os.environ.get("NEXUS_DASHBOARD_TOKEN", "")
        os.environ["NEXUS_DASHBOARD_TOKEN"] = "explicit-token"
        _GENERATED_TOKEN = ""
        val = _get_token()
        assert val == "explicit-token"
        if orig:
            os.environ["NEXUS_DASHBOARD_TOKEN"] = orig
        else:
            del os.environ["NEXUS_DASHBOARD_TOKEN"]

    def test_get_token_generates_when_not_set(self) -> None:
        from modules.web_ui.src.app import _get_token, _GENERATED_TOKEN

        import os
        orig = os.environ.get("NEXUS_DASHBOARD_TOKEN", "")
        if "NEXUS_DASHBOARD_TOKEN" in os.environ:
            del os.environ["NEXUS_DASHBOARD_TOKEN"]
        _GENERATED_TOKEN = ""
        val = _get_token()
        assert val != ""
        assert len(val) > 10
        if orig:
            os.environ["NEXUS_DASHBOARD_TOKEN"] = orig


class TestCostDashboardService:
    @pytest.mark.asyncio
    async def test_get_summary_empty(self) -> None:
        from modules.web_ui.src.app import CostDashboardService

        store = FakeEventStore()
        svc = CostDashboardService(store, None)
        result = await svc.get_summary()
        assert result["total_cost"] == 0.0
        assert result["per_tier"] == {}
        assert result["per_model"] == {}
        assert result["task_count"] == 0

    @pytest.mark.asyncio
    async def test_get_summary_with_events(self) -> None:
        from modules.web_ui.src.app import CostDashboardService

        store = FakeEventStore()
        for i in range(10):
            e = Event(
                event_type="cost_recorded",
                data={
                    "task_id": f"task_{i % 3}",
                    "amount": 0.01 * (i + 1),
                    "model": f"model_{i % 2}",
                    "tier": f"T{i % 4 + 1}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            store.events.append(e)
        svc = CostDashboardService(store, None)
        result = await svc.get_summary()
        expected_total = sum(0.01 * (i + 1) for i in range(10))
        assert result["total_cost"] == round(expected_total, 6)
        assert len(result["per_tier"]) == 4
        assert len(result["per_model"]) == 2
        assert result["task_count"] == 3

    @pytest.mark.asyncio
    async def test_get_tasks_pagination(self) -> None:
        from modules.web_ui.src.app import CostDashboardService

        store = FakeEventStore()
        for i in range(20):
            e = Event(
                event_type="cost_recorded",
                data={
                    "task_id": f"task_{i:03d}",
                    "amount": 0.01,
                    "model": "groq/llama3",
                    "tier": "T2",
                    "timestamp": f"2026-05-24T{10 + i // 60:02d}:{i % 60:02d}:00Z",
                },
            )
            store.events.append(e)
        svc = CostDashboardService(store, None)
        result = await svc.get_tasks(limit=5, offset=0)
        assert len(result) == 5
        timestamps = [t["timestamp"] for t in result]
        assert timestamps == sorted(timestamps, reverse=True)

    @pytest.mark.asyncio
    async def test_get_tasks_no_result(self) -> None:
        from modules.web_ui.src.app import CostDashboardService

        store = FakeEventStore()
        svc = CostDashboardService(store, None)
        result = await svc.get_tasks(limit=5, offset=100)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_task_detail_found(self) -> None:
        from modules.web_ui.src.app import CostDashboardService

        store = FakeEventStore()
        for i in range(3):
            e = Event(
                event_type="cost_recorded",
                data={
                    "task_id": "task_001",
                    "amount": 0.02 * (i + 1),
                    "model": "groq/llama3",
                    "tier": "T2",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            store.events.append(e)
        svc = CostDashboardService(store, None)
        result = await svc.get_task_detail("task_001")
        assert result is not None
        assert result["task_id"] == "task_001"
        assert result["total_cost"] == round(0.02 + 0.04 + 0.06, 6)
        assert len(result["steps"]) == 3

    @pytest.mark.asyncio
    async def test_get_task_detail_not_found(self) -> None:
        from modules.web_ui.src.app import CostDashboardService

        store = FakeEventStore()
        svc = CostDashboardService(store, None)
        result = await svc.get_task_detail("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_session_found(self) -> None:
        from modules.web_ui.src.app import CostDashboardService

        store = FakeEventStore()
        for i in range(3):
            e = Event(
                event_type="cost_recorded",
                data={
                    "task_id": f"ses_123_task_{i}",
                    "amount": 0.01,
                    "model": "groq/llama3",
                    "tier": "T1",
                    "timestamp": f"2026-05-24T1{i}:00:00Z",
                },
            )
            store.events.append(e)
        svc = CostDashboardService(store, None)
        result = await svc.get_session("ses_123")
        assert result is not None
        assert result["session_id"] == "ses_123"
        assert result["total_cost"] == round(0.03, 6)
        assert result["task_count"] == 3

    @pytest.mark.asyncio
    async def test_get_session_not_found(self) -> None:
        from modules.web_ui.src.app import CostDashboardService

        store = FakeEventStore()
        svc = CostDashboardService(store, None)
        result = await svc.get_session("nosession")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_tier_breakdown_empty(self) -> None:
        from modules.web_ui.src.app import CostDashboardService

        store = FakeEventStore()
        svc = CostDashboardService(store, None)
        result = await svc.get_tier_breakdown()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_model_breakdown(self) -> None:
        from modules.web_ui.src.app import CostDashboardService

        store = FakeEventStore()
        for i in range(4):
            e = Event(
                event_type="cost_recorded",
                data={
                    "task_id": f"task_{i}",
                    "amount": 0.01,
                    "model": f"model_{i % 2}",
                    "tier": "T1",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "latency_ms": 100.0,
                },
            )
            store.events.append(e)
        svc = CostDashboardService(store, None)
        result = await svc.get_model_breakdown()
        assert len(result) == 2
        for m in result:
            assert m["task_count"] == 2
            assert m["total_cost"] == round(0.02, 6)
            assert m["avg_latency_ms"] == 100.0

    @pytest.mark.asyncio
    async def test_get_etd_list_with_store(self) -> None:
        from modules.web_ui.src.app import CostDashboardService

        store = FakeEventStore()
        entry = FakeETDEntry(
            id="etd_001",
            intent_signature="deploy-web-app",
            success_count=5,
            failure_count=1,
            generalization_success_rate=0.8333,
            avg_cost=0.015,
            avg_latency_ms=1200.0,
        )
        indexed = FakeIndexedETDEntry(
            entry=entry,
            hit_count=10,
            created_at="2026-05-24T00:00:00Z",
        )

        class FakeETDStore:
            def list_all(self) -> list:
                return [indexed]

        svc = CostDashboardService(store, FakeETDStore())
        result = await svc.get_etd_list()
        assert len(result) == 1
        assert result[0]["id"] == "etd_001"
        assert result[0]["hit_rate"] == round(10 / 16, 4)
        assert result[0]["success_rate"] == 0.8333
        assert result[0]["avg_cost"] == 0.015
        assert result[0]["avg_latency_ms"] == 1200.0

    @pytest.mark.asyncio
    async def test_get_etd_list_no_store(self) -> None:
        from modules.web_ui.src.app import CostDashboardService

        store = FakeEventStore()
        svc = CostDashboardService(store, None)
        result = await svc.get_etd_list()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_tasks_date_range(self) -> None:
        from modules.web_ui.src.app import CostDashboardService

        store = FakeEventStore()
        store.events.append(Event(event_type="cost_recorded", data={
            "task_id": "task_early", "amount": 0.01, "model": "m1", "tier": "T1",
            "timestamp": "2026-05-01T00:00:00Z",
        }))
        store.events.append(Event(event_type="cost_recorded", data={
            "task_id": "task_mid", "amount": 0.02, "model": "m2", "tier": "T2",
            "timestamp": "2026-05-15T00:00:00Z",
        }))
        store.events.append(Event(event_type="cost_recorded", data={
            "task_id": "task_late", "amount": 0.03, "model": "m1", "tier": "T1",
            "timestamp": "2026-05-30T00:00:00Z",
        }))
        svc = CostDashboardService(store, None)
        result = await svc.get_tasks(start_date="2026-05-10T00:00:00Z", end_date="2026-05-20T00:00:00Z")
        assert len(result) == 1
        assert result[0]["task_id"] == "task_mid"

    @pytest.mark.asyncio
    async def test_get_tasks_cost_range(self) -> None:
        from modules.web_ui.src.app import CostDashboardService

        store = FakeEventStore()
        for i in range(5):
            store.events.append(Event(event_type="cost_recorded", data={
                "task_id": f"task_{i}", "amount": 0.01 * (i + 1), "model": "m1", "tier": "T1",
                "timestamp": "2026-05-24T00:00:00Z",
            }))
        svc = CostDashboardService(store, None)
        result = await svc.get_tasks(cost_min=0.03, cost_max=0.05)
        task_ids = [t["task_id"] for t in result]
        assert "task_2" in task_ids
        assert "task_3" in task_ids
        assert "task_4" in task_ids

    @pytest.mark.asyncio
    async def test_get_audit_log_with_model_filter(self) -> None:
        from modules.web_ui.src.app import CostDashboardService

        store = FakeEventStore()
        store.events.append(Event(event_type="cost_recorded", data={
            "task_id": "task_a", "amount": 0.01, "model": "groq/llama3", "tier": "T1",
            "timestamp": "2026-05-24T10:00:00Z",
        }))
        store.events.append(Event(event_type="cost_recorded", data={
            "task_id": "task_b", "amount": 0.02, "model": "local/mock", "tier": "T2",
            "timestamp": "2026-05-24T11:00:00Z",
        }))
        svc = CostDashboardService(store, None)
        result = await svc.get_audit_log(model="local/mock")
        assert len(result) == 1
        assert result[0]["task_id"] == "task_b"

    @pytest.mark.asyncio
    async def test_get_audit_log_date_range(self) -> None:
        from modules.web_ui.src.app import CostDashboardService

        store = FakeEventStore()
        store.events.append(Event(event_type="cost_recorded", data={
            "task_id": "task_1", "amount": 0.01, "model": "m1", "tier": "T1",
            "timestamp": "2026-05-01T00:00:00Z",
        }))
        store.events.append(Event(event_type="cost_recorded", data={
            "task_id": "task_2", "amount": 0.02, "model": "m2", "tier": "T2",
            "timestamp": "2026-05-15T00:00:00Z",
        }))
        svc = CostDashboardService(store, None)
        result = await svc.get_audit_log(start_date="2026-05-10T00:00:00Z")
        assert len(result) == 1
        assert result[0]["task_id"] == "task_2"

    @pytest.mark.asyncio
    async def test_get_audit_log_cost_max_only(self) -> None:
        from modules.web_ui.src.app import CostDashboardService

        store = FakeEventStore()
        for i in range(5):
            store.events.append(Event(event_type="cost_recorded", data={
                "task_id": f"task_{i}", "amount": 0.01 * (i + 1),
                "model": "m1", "tier": "T1",
                "timestamp": "2026-05-24T00:00:00Z",
            }))
        svc = CostDashboardService(store, None)
        result = await svc.get_audit_log(cost_max=0.02)
        assert len(result) == 2
        for r in result:
            assert r["cost"] <= 0.02

    @pytest.mark.asyncio
    async def test_get_audit_log_date_filters(self) -> None:
        from modules.web_ui.src.app import CostDashboardService

        store = FakeEventStore()
        store.events.append(Event(event_type="cost_recorded", data={
            "task_id": "task_early", "amount": 0.01, "model": "m1", "tier": "T1",
            "timestamp": "2026-05-01T00:00:00Z",
        }))
        store.events.append(Event(event_type="cost_recorded", data={
            "task_id": "task_mid", "amount": 0.02, "model": "m2", "tier": "T2",
            "timestamp": "2026-05-15T00:00:00Z",
        }))
        svc = CostDashboardService(store, None)
        result = await svc.get_audit_log(end_date="2026-05-10T00:00:00Z")
        assert len(result) == 1
        assert result[0]["task_id"] == "task_early"

    @pytest.mark.asyncio
    async def test_get_tasks_cost_max(self) -> None:
        from modules.web_ui.src.app import CostDashboardService

        store = FakeEventStore()
        for i in range(3):
            store.events.append(Event(event_type="cost_recorded", data={
                "task_id": f"task_{i}", "amount": 0.01 * (i + 1),
                "model": "m1", "tier": "T1",
                "timestamp": "2026-05-24T00:00:00Z",
            }))
        svc = CostDashboardService(store, None)
        result = await svc.get_tasks(cost_max=0.02)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_audit_log_filters(self) -> None:
        from modules.web_ui.src.app import CostDashboardService

        store = FakeEventStore()
        for i in range(10):
            e = Event(
                event_type="cost_recorded",
                data={
                    "task_id": f"task_{i % 2}",
                    "amount": 0.01 * (i + 1),
                    "model": "groq/llama3",
                    "tier": "T2",
                    "timestamp": f"2026-05-24T{10 + i:02d}:00:00Z",
                },
            )
            store.events.append(e)
        svc = CostDashboardService(store, None)
        result = await svc.get_audit_log(task_id="task_0", limit=5, offset=0)
        assert len(result) == 5
        for r in result:
            assert r["task_id"] == "task_0"
        assert result[0]["timestamp"] >= result[-1]["timestamp"]

    @pytest.mark.asyncio
    async def test_get_audit_log_cost_range(self) -> None:
        from modules.web_ui.src.app import CostDashboardService

        store = FakeEventStore()
        for i in range(5):
            e = Event(
                event_type="cost_recorded",
                data={
                    "task_id": f"task_{i}",
                    "amount": 0.01 * (i + 1),
                    "model": "groq/llama3",
                    "tier": "T2",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            store.events.append(e)
        svc = CostDashboardService(store, None)
        result = await svc.get_audit_log(cost_min=0.03, cost_max=0.05)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_get_tasks_empty_task_id_skipped(self) -> None:
        from modules.web_ui.src.app import CostDashboardService

        store = FakeEventStore()
        store.events.append(Event(
            event_type="cost_recorded",
            data={
                "task_id": "", "amount": 0.01, "model": "m1", "tier": "T1",
                "timestamp": "2026-05-24T00:00:00Z",
            },
        ))
        store.events.append(Event(
            event_type="cost_recorded",
            data={
                "task_id": "real_task", "amount": 0.02, "model": "m2", "tier": "T2",
                "timestamp": "2026-05-24T01:00:00Z",
            },
        ))
        svc = CostDashboardService(store, None)
        result = await svc.get_tasks()
        assert len(result) == 1
        assert result[0]["task_id"] == "real_task"

    @pytest.mark.asyncio
    async def test_get_task_events_method(self) -> None:
        from modules.web_ui.src.app import CostDashboardService

        store = FakeEventStore()
        store.events.append(Event(
            event_type="task_completed",
            data={"task_id": "t1", "result": "ok"},
        ))
        svc = CostDashboardService(store, None)
        result = await svc._get_task_events()
        assert len(result) == 1
        assert result[0].event_type == "task_completed"

    def test_cost_dashboard_error_code_and_message(self) -> None:
        from modules.web_ui.src.app import CostDashboardError

        err = CostDashboardError("CD-999", "test error message")
        assert err.code == "CD-999"
        assert str(err) == "test error message"

    def test_index_html_returns_content(self) -> None:
        from modules.web_ui.src.app import index_html

        result = index_html()
        assert "NEXUS-R" in result or "<!DOCTYPE" in result

    def test_index_html_fallback_to_template(self) -> None:
        from modules.web_ui.src.app import index_html
        import os

        original_path = os.path.join(os.path.dirname(__file__),
                                     "../../modules/web_ui/src/static/index.html")
        abs_path = os.path.abspath(original_path)
        if os.path.isfile(abs_path):
            with patch("os.path.isfile", return_value=False):
                result = index_html()
                assert "Static files not found" in result
                assert "NEXUS-R Cost Dashboard" in result

    @pytest.mark.asyncio
    async def test_get_session_mixed_ids(self) -> None:
        from modules.web_ui.src.app import CostDashboardService

        store = FakeEventStore()
        for i in range(3):
            store.events.append(Event(event_type="cost_recorded", data={
                "task_id": f"ses_abc_task_{i}" if i < 2 else f"other_{i}",
                "amount": 0.01, "model": "m1", "tier": "T1",
                "timestamp": f"2026-05-24T{i}:00:00Z",
            }))
        svc = CostDashboardService(store, None)
        result = await svc.get_session("ses_abc")
        assert result is not None
        assert result["task_count"] == 2

    @pytest.mark.asyncio
    async def test_get_tasks_updates_timestamp_model_tier(self) -> None:
        from modules.web_ui.src.app import CostDashboardService

        store = FakeEventStore()
        store.events.append(Event(event_type="cost_recorded", data={
            "task_id": "task_same", "amount": 0.01, "model": "old_model", "tier": "T1",
            "timestamp": "2026-05-24T00:00:00Z",
        }))
        store.events.append(Event(event_type="cost_recorded", data={
            "task_id": "task_same", "amount": 0.02, "model": "new_model", "tier": "T2",
            "timestamp": "2026-05-25T00:00:00Z",
        }))
        svc = CostDashboardService(store, None)
        result = await svc.get_tasks()
        assert len(result) == 1
        assert result[0]["model"] == "new_model"
        assert result[0]["tier"] == "T2"
        assert result[0]["step_count"] == 2


class TestCostWebSocketHandler:
    @pytest.mark.asyncio
    async def test_notify_cost_update_tracks_running_total(self) -> None:
        from modules.web_ui.src.app import CostWebSocketHandler

        handler = CostWebSocketHandler()
        await handler.notify_cost_update("task_001", 0.01, "m1", "T1")
        await handler.notify_cost_update("task_002", 0.02, "m2", "T2")
        await handler.notify_cost_update("task_003", 0.03, "m1", "T1")
        assert handler._running_total == 0.06

    @pytest.mark.asyncio
    async def test_reset_clears_running_total(self) -> None:
        from modules.web_ui.src.app import CostWebSocketHandler

        handler = CostWebSocketHandler()
        await handler.notify_cost_update("task_001", 0.05, "m1", "T1")
        await handler.reset()
        assert handler._running_total == 0.0

    @pytest.mark.asyncio
    async def test_broadcast_puts_messages_in_queues(self) -> None:
        from modules.web_ui.src.app import CostWebSocketHandler

        handler = CostWebSocketHandler()
        mock_ws = AsyncMock()

        class FakeWS:
            close_code = None
            async def accept(self): pass
            async def receive_text(self): raise Exception("done")
            async def send_json(self, data): await mock_ws.send_json(data)
            async def close(self, code=None): self.close_code = code

        fake = FakeWS()
        handler._connections["all"].append(fake)
        buf = asyncio.Queue()
        handler._send_buffers[id(fake)] = buf

        await handler.broadcast({"type": "cost_update", "tier": "T1"})
        assert buf.qsize() == 1
        msg = buf.get_nowait()
        assert msg["type"] == "cost_update"

    @pytest.mark.asyncio
    async def test_notify_cost_update_broadcasts_to_queue(self) -> None:
        from modules.web_ui.src.app import CostWebSocketHandler

        handler = CostWebSocketHandler()
        mock_ws = AsyncMock()

        class FakeWS:
            close_code = None
            async def accept(self): pass
            async def receive_text(self): raise Exception("done")
            async def send_json(self, data): await mock_ws.send_json(data)
            async def close(self, code=None): self.close_code = code

        fake = FakeWS()
        handler._connections["all"].append(fake)
        buf = asyncio.Queue()
        handler._send_buffers[id(fake)] = buf

        await handler.notify_cost_update("task_001", 0.02, "groq/llama3", "T2")
        assert buf.qsize() == 1
        msg = buf.get_nowait()
        assert msg["type"] == "cost_update"
        assert msg["task_id"] == "task_001"
        assert msg["cost"] == 0.02

    @pytest.mark.asyncio
    async def test_notify_task_started_and_completed_queue(self) -> None:
        from modules.web_ui.src.app import CostWebSocketHandler

        handler = CostWebSocketHandler()
        mock_ws = AsyncMock()

        class FakeWS:
            close_code = None
            async def accept(self): pass
            async def receive_text(self): raise Exception("done")
            async def send_json(self, data): await mock_ws.send_json(data)
            async def close(self, code=None): self.close_code = code

        fake = FakeWS()
        handler._connections["all"].append(fake)
        buf = asyncio.Queue()
        handler._send_buffers[id(fake)] = buf

        await handler.notify_task_started("task_001", 0.01)
        msg1 = buf.get_nowait()
        assert msg1["type"] == "task_started"
        assert msg1["task_id"] == "task_001"

        await handler.notify_task_completed("task_001", 0.02, 150.0)
        msg2 = buf.get_nowait()
        assert msg2["type"] == "task_completed"
        assert msg2["task_id"] == "task_001"
        assert msg2["final_cost"] == 0.02

    @pytest.mark.asyncio
    async def test_session_reset_broadcasts(self) -> None:
        from modules.web_ui.src.app import CostWebSocketHandler

        handler = CostWebSocketHandler()
        mock_ws = AsyncMock()

        class FakeWS:
            close_code = None
            async def accept(self): pass
            async def receive_text(self): raise Exception("done")
            async def send_json(self, data): await mock_ws.send_json(data)
            async def close(self, code=None): self.close_code = code

        fake = FakeWS()
        handler._connections["all"].append(fake)
        buf = asyncio.Queue()
        handler._send_buffers[id(fake)] = buf

        handler._running_total = 5.0
        await handler.reset()
        assert handler._running_total == 0.0
        msg = buf.get_nowait()
        assert msg["type"] == "session_reset"

    @pytest.mark.asyncio
    async def test_broadcast_without_connections_no_error(self) -> None:
        from modules.web_ui.src.app import CostWebSocketHandler

        handler = CostWebSocketHandler()
        await handler.broadcast({"type": "cost_update"})
        await handler.notify_cost_update("task_001", 0.01, "m1", "T1")


class TestCostTrackerIntegration:
    @pytest.mark.asyncio
    async def test_record_sends_to_event_store(self) -> None:
        store = FakeEventStore()
        ct = CostTracker(store)
        await ct.record("task_001", 0.01, "groq/llama3", PermissionTier.T1)
        events = await store.get_by_type("cost_recorded")
        assert len(events) == 1
        assert events[0].data["task_id"] == "task_001"
        assert float(events[0].data["amount"]) == 0.01

    @pytest.mark.asyncio
    async def test_record_with_ws_handler(self) -> None:
        store = FakeEventStore()
        ws_handler = AsyncMock()
        ws_handler.notify_cost_update = AsyncMock()
        ct = CostTracker(store, ws_handler)
        await ct.record("task_001", 0.02, "groq/llama3", PermissionTier.T2)
        events = await store.get_by_type("cost_recorded")
        assert len(events) == 1
        assert ws_handler.notify_cost_update.called
        call_kwargs = ws_handler.notify_cost_update.call_args[1]
        assert call_kwargs["task_id"] == "task_001"
        assert call_kwargs["amount"] == 0.02

    @pytest.mark.asyncio
    async def test_summary_aggregates_correctly(self) -> None:
        store = FakeEventStore()
        ct = CostTracker(store)
        await ct.record("task_001", 0.01, "groq/llama3", PermissionTier.T1)
        await ct.record("task_001", 0.02, "groq/llama3", PermissionTier.T1)
        await ct.record("task_002", 0.03, "local/mock", PermissionTier.T2)
        summary = await ct.summary()
        assert summary["totals"]["total_cost"] == 0.06
        assert len(summary["per_task"]) == 2
        assert summary["per_task"]["task_001"] == 0.03
