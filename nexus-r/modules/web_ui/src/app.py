from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Depends, WebSocket, BackgroundTasks, Query, WebSocketDisconnect, status
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator

from nexus_r.events import Event, PermissionTier
from nexus_r.memory import MemoryManager, ModelOrchestrator, memory_router
from nexus_r.memory.vector_store import VectorStore
from nexus_r.memory.routes import inject_manager as inject_memory_manager


class DownloadRequest(BaseModel):
    model_name: str
    url: str = ""

class DeleteRequest(BaseModel):
    model_name: str


class TestRequest(BaseModel):
    local_model: str | None = None
    cloud_provider: str | None = None
    api_key: str | None = None


class ConfigureRequest(BaseModel):
    local_model: str | None = None
    cloud_provider: str | None = None
    api_key: str | None = None

class RoutingProfile(BaseModel):
    router: str | None = None
    reasoning: str | None = None
    coding: str | None = None
    general: str | None = None
    embedding: str | None = None

class ConfigRequest(BaseModel):
    local_model: str | None = None
    cloud_provider: str | None = None
    api_key: str | None = None
    routingProfile: RoutingProfile | None = None

class ChatRequest(BaseModel):
    message: str = Field(..., max_length=10000)
    model: str | None = None
    conversation_id: str | None = None
    images: list[str] | None = None
    mode: str = "balanced"
    search_enabled: bool = False
    search_sources: list[str] = Field(default_factory=lambda: ["web"])

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        if v not in ("speed", "balanced", "quality"):
            raise ValueError('mode must be "speed", "balanced", or "quality"')
        return v

    @field_validator("search_sources")
    @classmethod
    def validate_search_sources(cls, v: list[str]) -> list[str]:
        allowed = {"web", "news", "academic", "social"}
        for s in v:
            if s not in allowed:
                raise ValueError(f"Invalid search source: {s}. Allowed: {', '.join(sorted(allowed))}")
        return v

class HITLResumeRequest(BaseModel):
    message_id: str
    code: str | None = None
    solved: bool = False

class TruncateRequest(BaseModel):
    message_id: str
    keep_inclusive: bool = True

class FeedbackRequest(BaseModel):
    feedback: str

class SuggestionRequest(BaseModel):
    prefix: str = Field(..., min_length=1, max_length=200)
    limit: int = Field(5, ge=1, le=20)

class TelemetryBatch(BaseModel):
    signals: list[dict[str, Any]]
    session_id: str | None = None

logger = logging.getLogger("nexus-r.dashboard")

_GENERATED_TOKEN: str = ""


def _get_token() -> str:
    global _GENERATED_TOKEN
    token = os.environ.get("NEXUS_DASHBOARD_TOKEN", "")
    if not token:
        if not _GENERATED_TOKEN:
            _GENERATED_TOKEN = str(uuid4())
            logger.warning(
                "Generated ephemeral dashboard token in memory; set NEXUS_DASHBOARD_TOKEN for controlled access."
            )
        return _GENERATED_TOKEN
    return token

RATE_LIMIT_MAX = 100
RATE_LIMIT_WINDOW = 60


class RateLimitExceeded(Exception):
    pass


class CostDashboardError(Exception):
    code: str

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class CostDashboardService:
    def __init__(self, event_store, etd_store: Any | None = None) -> None:
        self.event_store = event_store
        self.etd_store = etd_store
        self._initialized = False

    async def initialize(self) -> None:
        if self._initialized:
            return
        await self.event_store.initialize()
        self._initialized = True

    async def _get_cost_events(self) -> list[Event]:
        await self.initialize()
        return await self.event_store.get_by_type("cost_recorded")

    async def _get_task_events(self) -> list[Event]:
        await self.initialize()
        return await self.event_store.get_by_type("task_completed")

    async def get_summary(self) -> dict[str, Any]:
        events = await self._get_cost_events()
        total_cost = 0.0
        per_tier: dict[str, float] = {}
        per_model: dict[str, float] = {}
        task_ids: set[str] = set()
        for event in events:
            data = event.data
            amount = float(data.get("amount", 0))
            total_cost += amount
            tier = str(data.get("tier", "unknown"))
            model = str(data.get("model", "unknown"))
            per_tier[tier] = per_tier.get(tier, 0.0) + amount
            per_model[model] = per_model.get(model, 0.0) + amount
            task_ids.add(str(data.get("task_id", "")))
        return {
            "total_cost": round(total_cost, 6),
            "per_tier": {k: round(v, 6) for k, v in per_tier.items()},
            "per_model": {k: round(v, 6) for k, v in per_model.items()},
            "task_count": len(task_ids),
        }

    async def get_tasks(
        self,
        limit: int = 50,
        offset: int = 0,
        tier: str | None = None,
        model: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        cost_min: float | None = None,
        cost_max: float | None = None,
    ) -> list[dict[str, Any]]:
        events = await self._get_cost_events()
        task_map: dict[str, dict[str, Any]] = {}
        for event in events:
            data = event.data
            task_id = str(data.get("task_id", ""))
            if not task_id:
                continue
            event_tier = str(data.get("tier", ""))
            event_model = str(data.get("model", ""))
            event_ts = str(data.get("timestamp", ""))
            event_amount = float(data.get("amount", 0))
            if tier and event_tier != tier:
                continue
            if model and event_model != model:
                continue
            if start_date and event_ts < start_date:
                continue
            if end_date and event_ts > end_date:
                continue
            if task_id not in task_map:
                task_map[task_id] = {
                    "task_id": task_id,
                    "total_cost": 0.0,
                    "model": event_model,
                    "tier": event_tier,
                    "timestamp": event_ts,
                    "action_type": str(data.get("action_type", "general_llm")),
                    "step_count": 0,
                }
            entry = task_map[task_id]
            entry["total_cost"] += event_amount
            entry["step_count"] += 1
            if event_ts > entry["timestamp"]:
                entry["timestamp"] = event_ts
                entry["model"] = event_model
                entry["tier"] = event_tier
        results = sorted(task_map.values(), key=lambda t: t["timestamp"], reverse=True)
        paginated = results[offset:offset + limit]
        for r in paginated:
            cost = r["total_cost"]
            if cost_min is not None and cost < cost_min:
                continue
            if cost_max is not None and cost > cost_max:
                continue
            r["total_cost"] = round(cost, 6)
        if cost_min is not None or cost_max is not None:
            paginated = [r for r in paginated
                         if (cost_min is None or r["total_cost"] >= cost_min)
                         and (cost_max is None or r["total_cost"] <= cost_max)]
        count = len(task_map)
        if count > 5000:
            raise CostDashboardError("CD-007", f"Query matches {count} rows; set tighter filter or pagination")
        return paginated

    async def get_task_detail(self, task_id: str) -> dict[str, Any] | None:
        events = await self._get_cost_events()
        steps: list[dict[str, Any]] = []
        total_cost = 0.0
        for event in events:
            data = event.data
            if str(data.get("task_id", "")) != task_id:
                continue
            amount = float(data.get("amount", 0))
            total_cost += amount
            steps.append({
                "step": len(steps) + 1,
                "cost": round(amount, 6),
                "model": str(data.get("model", "")),
                "tier": str(data.get("tier", "")),
                "timestamp": str(data.get("timestamp", "")),
            })
        if not steps:
            return None
        return {
            "task_id": task_id,
            "total_cost": round(total_cost, 6),
            "steps": steps,
        }

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        events = await self._get_cost_events()
        total_cost = 0.0
        task_ids: set[str] = set()
        timestamps: list[str] = []
        for event in events:
            data = event.data
            tid = str(data.get("task_id", ""))
            if not tid.startswith(session_id):
                continue
            total_cost += float(data.get("amount", 0))
            task_ids.add(tid)
            timestamps.append(str(data.get("timestamp", "")))
        if not task_ids:
            return None
        return {
            "session_id": session_id,
            "total_cost": round(total_cost, 6),
            "task_count": len(task_ids),
            "first_seen": min(timestamps) if timestamps else "",
            "last_seen": max(timestamps) if timestamps else "",
        }

    async def get_tier_breakdown(self) -> list[dict[str, Any]]:
        events = await self._get_cost_events()
        tiers: dict[str, dict[str, Any]] = {}
        for event in events:
            data = event.data
            tier = str(data.get("tier", "unknown"))
            amount = float(data.get("amount", 0))
            if tier not in tiers:
                tiers[tier] = {"tier": tier, "total_cost": 0.0, "task_count": 0}
            tiers[tier]["total_cost"] += amount
            tiers[tier]["task_count"] = len({
                str(e.data.get("task_id", ""))
                for e in self.event_store._cached_events
                if hasattr(self.event_store, '_cached_events')
            }) if hasattr(self.event_store, '_get_cost_events') else 0
        for t_data in tiers.values():
            t_data["avg_cost"] = round(t_data["total_cost"] / t_data["task_count"], 6) if t_data["task_count"] > 0 else 0.0
            t_data["total_cost"] = round(t_data["total_cost"], 6)
        return list(tiers.values())

    async def get_model_breakdown(self) -> list[dict[str, Any]]:
        events = await self._get_cost_events()
        models: dict[str, dict[str, Any]] = {}
        for event in events:
            data = event.data
            model = str(data.get("model", "unknown"))
            amount = float(data.get("amount", 0))
            latency = float(data.get("latency_ms", 0))
            if model not in models:
                models[model] = {"model": model, "total_cost": 0.0, "task_count": 0, "total_latency": 0.0}
            models[model]["total_cost"] += amount
            models[model]["task_count"] += 1
            models[model]["total_latency"] += latency
        results = []
        for m_data in models.values():
            results.append({
                "model": m_data["model"],
                "total_cost": round(m_data["total_cost"], 6),
                "task_count": m_data["task_count"],
                "avg_latency_ms": round(m_data["total_latency"] / m_data["task_count"], 2) if m_data["task_count"] > 0 else 0.0,
            })
        return results

    async def get_etd_list(self) -> list[dict[str, Any]]:
        if self.etd_store is None:
            return []
        entries = self.etd_store.list_all()
        results = []
        for ie in entries:
            total = ie.hit_count + ie.entry.success_count + ie.entry.failure_count
            hit_rate = round(ie.hit_count / total, 4) if total > 0 else 0.0
            success_rate = round(ie.entry.generalization_success_rate, 4)
            results.append({
                "id": ie.entry.id,
                "intent_signature": ie.entry.intent_signature,
                "hit_count": ie.hit_count,
                "success_count": ie.entry.success_count,
                "failure_count": ie.entry.failure_count,
                "hit_rate": hit_rate,
                "success_rate": success_rate,
                "avg_cost": round(ie.entry.avg_cost, 6),
                "avg_latency_ms": round(ie.entry.avg_latency_ms, 2),
                "invalidated": ie.invalidated,
                "created_at": ie.created_at,
            })
        return results

    async def get_audit_log(
        self,
        limit: int = 50,
        offset: int = 0,
        task_id: str | None = None,
        model: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        cost_min: float | None = None,
        cost_max: float | None = None,
    ) -> list[dict[str, Any]]:
        events = await self._get_cost_events()
        results = []
        for event in events:
            data = event.data
            if task_id and str(data.get("task_id", "")) != task_id:
                continue
            if model and str(data.get("model", "")) != model:
                continue
            ts = str(data.get("timestamp", ""))
            if start_date and ts < start_date:
                continue
            if end_date and ts > end_date:
                continue
            amount = float(data.get("amount", 0))
            if cost_min is not None and amount < cost_min:
                continue
            if cost_max is not None and amount > cost_max:
                continue
            results.append({
                "task_id": str(data.get("task_id", "")),
                "cost": round(amount, 6),
                "model": str(data.get("model", "")),
                "tier": str(data.get("tier", "")),
                "timestamp": ts,
                "action_type": str(data.get("action_type", "general_llm")),
            })
        results.sort(key=lambda r: r["timestamp"], reverse=True)
        return results[offset:offset + limit]


class CostWebSocketHandler:
    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = defaultdict(list)
        self._running_total: float = 0.0
        self._send_buffers: dict[str, asyncio.Queue] = {}

    async def handle(self, websocket: WebSocket) -> None:
        await websocket.accept()
        current_filter = "all"
        self._connections[current_filter].append(websocket)
        buffer: asyncio.Queue = asyncio.Queue(maxsize=256)
        self._send_buffers[id(websocket)] = buffer
        send_task = asyncio.create_task(self._send_loop(websocket, buffer))
        try:
            while True:
                raw = await websocket.receive_text()
                if isinstance(raw, str) and raw.startswith("{"):
                    import json
                    try:
                        msg = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    msg_type = msg.get("type")
                    if msg_type == "subscribe":
                        self._connections[current_filter].remove(websocket)
                        if not self._connections[current_filter]:
                            del self._connections[current_filter]
                        new_filter = msg.get("filter", "all")
                        if new_filter not in ("all",) and not new_filter.startswith(("tier:", "model:")):
                            await websocket.send_json({"error": "CD-006", "message": f"Invalid WebSocket filter: {new_filter}"})
                            continue
                        current_filter = new_filter
                        self._connections[current_filter].append(websocket)
                    elif msg_type == "unsubscribe":
                        self._connections[current_filter].remove(websocket)
                        if not self._connections[current_filter]:
                            del self._connections[current_filter]
                        current_filter = "all"
                        self._connections[current_filter].append(websocket)
        except WebSocketDisconnect:
            pass
        except Exception:
            pass
        finally:
            send_task.cancel()
            try:
                await send_task
            except (asyncio.CancelledError, Exception):
                pass
            if current_filter in self._connections and websocket in self._connections[current_filter]:
                self._connections[current_filter].remove(websocket)
                if not self._connections[current_filter]:
                    del self._connections[current_filter]
            buf_key = id(websocket)
            if buf_key in self._send_buffers:
                del self._send_buffers[buf_key]

    async def _send_loop(self, websocket: WebSocket, buffer: asyncio.Queue) -> None:
        while True:
            try:
                msg = await asyncio.wait_for(buffer.get(), timeout=30)
                try:
                    await websocket.send_json(msg)
                except Exception:
                    break
            except asyncio.TimeoutError:
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break

    async def broadcast(self, message: dict[str, Any]) -> None:
        for filter_key, connections in list(self._connections.items()):
            if filter_key == "all":
                targets = connections[:]
            elif message.get("tier") and filter_key == f"tier:{message['tier']}":
                targets = connections[:]
            elif message.get("model") and filter_key == f"model:{message['model']}":
                targets = connections[:]
            else:
                continue
            for ws in targets:
                buf = self._send_buffers.get(id(ws))
                if buf is None:
                    continue
                try:
                    buf.put_nowait(message)
                except asyncio.QueueFull:
                    try:
                        buf.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                    try:
                        buf.put_nowait(message)
                    except asyncio.QueueFull:
                        logger.warning("WebSocket send buffer full for connection %s", id(ws))

    async def notify_cost_update(self, task_id: str, amount: float, model: str, tier: str, running_total: float | None = None) -> None:
        self._running_total += amount
        rt = running_total if running_total is not None else self._running_total
        await self.broadcast({
            "type": "cost_update",
            "task_id": task_id,
            "cost": round(amount, 6),
            "model": model,
            "tier": tier,
            "running_total": round(rt, 6),
        })

    async def notify_task_started(self, task_id: str, estimated_cost: float = 0.0) -> None:
        await self.broadcast({
            "type": "task_started",
            "task_id": task_id,
            "estimated_cost": round(estimated_cost, 6),
        })

    async def notify_task_completed(self, task_id: str, final_cost: float, latency_ms: float) -> None:
        await self.broadcast({
            "type": "task_completed",
            "task_id": task_id,
            "final_cost": round(final_cost, 6),
            "latency_ms": round(latency_ms, 2),
        })

    async def reset(self) -> None:
        self._running_total = 0.0
        await self.broadcast({"type": "session_reset", "total_cost": 0.0})


_ws_handler: CostWebSocketHandler | None = None
_dashboard_service: CostDashboardService | None = None
_chat_handler: Any = None
_model_manager: Any = None
_secret_registry: Any = None
_rate_limiter: dict[str, list[float]] = defaultdict(list)


def create_app(event_store, etd_store=None, chat_handler=None, config=None, **kwargs) -> FastAPI:
    global _ws_handler, _dashboard_service, _chat_handler, _model_manager
    app = FastAPI(title="NEXUS-R Cost Dashboard", version="0.2.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    _ws_handler = CostWebSocketHandler()
    _dashboard_service = CostDashboardService(event_store, etd_store)

    # Resolve config, router, and secret_registry
    cfg = config
    router = None
    global _secret_registry
    _secret_registry = None

    # Initialize MemoryManager + ModelOrchestrator in either branch
    _memory_manager: MemoryManager | None = None
    _orchestrator: ModelOrchestrator | None = None

    if chat_handler is not None:
        _chat_handler = chat_handler
        router = getattr(_chat_handler, "router", None)
        if router is not None:
            cfg = getattr(router, "config", None)
            models = getattr(router, "models", None)
            if models is not None:
                _secret_registry = getattr(models, "secret_registry", None)
        # Initialize memory + orchestrator using the injected chat_handler's router
        if router is not None and getattr(router, "models", None) is not None:
            _db_path = os.environ.get("NEXUS_MEMORY_DB", "nexus_memory.db")
            _vector_store = VectorStore()
            _memory_manager = MemoryManager(db_path=_db_path, vector_store=_vector_store)
            inject_memory_manager(_memory_manager)
            asyncio.create_task(_memory_manager.initialize())
            app.include_router(memory_router)
            _orchestrator = ModelOrchestrator(
                memory_manager=_memory_manager,
                model_registry=router.models,
            )
    else:
        # Initialize default ChatHandler if none provided
        from modules.web_ui.src.chat_handler import ChatHandler
        from modules.cognition_router.src.router import CognitionRouter
        from modules.trust_layer.src.cost_tracker import CostTracker
        from modules.trust_layer.src.permission_enforcer import PermissionEnforcer
        from modules.trust_layer.src.secret_registry import SecretRegistry
        from modules.cognition_router.src.vision_processor import VisionProcessor
        from nexus_r.config import NEXUSConfig

        cfg = config or NEXUSConfig.from_env(os.getcwd())
        _secret_registry = SecretRegistry(cfg.app_name)
        _secret_registry.bootstrap_from_environment(
            cfg.models.byok_secret_name,
            cfg.models.byok_api_key_env,
        )
        _secret_registry.bootstrap_from_environment(
            "openrouter_api_key",
            "NEXUS_OPENROUTER_API_KEY",
        )

        router = CognitionRouter(
            cfg,
            event_store,
            _secret_registry,
        )
        permission_enforcer = PermissionEnforcer()
        cost_tracker = CostTracker(event_store)

        # Initialize MemoryManager with SQLite + ChromaDB persistence
        _db_path = os.environ.get("NEXUS_MEMORY_DB", "nexus_memory.db")
        _vector_store = VectorStore()
        _memory_manager = MemoryManager(db_path=_db_path, vector_store=_vector_store)
        inject_memory_manager(_memory_manager)
        app.include_router(memory_router)

        _chat_handler = ChatHandler(
            event_store=event_store,
            cost_tracker=cost_tracker,
            router=router,
            ws_handler=_ws_handler,
            perms=permission_enforcer,
            vision_processor=VisionProcessor(),
            memory_manager=_memory_manager,
        )

        # Initialize ModelOrchestrator — bridges BlackboardState + ModelRegistry
        _orchestrator = ModelOrchestrator(
            memory_manager=_memory_manager,
            model_registry=router.models,
        )

    if cfg is None:
        from nexus_r.config import NEXUSConfig
        cfg = NEXUSConfig.from_env(os.getcwd())

    # Initialize ModelManager
    from modules.cognition_router.src.model_manager import ModelManager

    _model_manager = ModelManager(
        config=cfg,
        event_store=event_store,
        router=router,
        secret_registry=_secret_registry,
    )

    @app.on_event("startup")
    async def startup() -> None:
        await _memory_manager.initialize()
        await _dashboard_service.initialize()
        if _model_manager is not None:
            try:
                _model_manager.apply_saved_config()
                logger.info("Successfully loaded and applied model configuration on startup.")
            except Exception as exc:
                logger.warning("Failed to apply saved model configuration on startup: %s", exc)
        logger.info("Cost dashboard initialized on port 8400")
        logger.info("Dashboard UI: http://localhost:8400")
        logger.info("API docs: http://localhost:8400/docs")
        if os.environ.get("NEXUS_DASHBOARD_TOKEN"):
            logger.info("Dashboard auth token configured via environment.")
        else:
            logger.warning("Dashboard started with generated in-memory token only.")

    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.isdir(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    async def root():
        return HTMLResponse(content=index_html(), status_code=200)

    @app.get("/api/v1/dashboard")
    async def dashboard_html(token: str = Query("")):
        _check_auth(token)
        return HTMLResponse(content=index_html(), status_code=200)

    @app.get("/api/v1/auth/token")
    async def get_auth_token():
        return {"token": _get_token()}

    @app.post("/api/v1/telemetry")
    async def receive_telemetry(batch: TelemetryBatch, token: str = Query("")):
        _check_auth(token)
        if _chat_handler:
            for signal in batch.signals:
                _chat_handler.behavior_tracker.record_signal(
                    signal.get("type", "unknown"),
                    signal.get("value")
                )
        return {"received": len(batch.signals)}

    # Memory endpoints are handled by nexus_r.memory.routes (injected above)

    @app.get("/api/v1/cost/summary")
    async def get_summary(token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("summary")
        if _dashboard_service is None:
            raise HTTPException(status_code=500, detail="CD-001: Cost dashboard service not initialized")
        try:
            return await _dashboard_service.get_summary()
        except CostDashboardError as e:
            raise HTTPException(status_code=400, detail=f"{e.code}: {e.args[0]}")

    @app.get("/api/v1/cost/tasks")
    async def get_tasks(
        token: str = Query(""),
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
        tier: str | None = Query(None),
        model: str | None = Query(None),
        start_date: str | None = Query(None),
        end_date: str | None = Query(None),
        cost_min: float | None = Query(None, ge=0),
        cost_max: float | None = Query(None, ge=0),
    ):
        _check_auth(token)
        _check_rate_limit("tasks")
        if _dashboard_service is None:
            raise HTTPException(status_code=500, detail="CD-001: Cost dashboard service not initialized")
        try:
            return await _dashboard_service.get_tasks(
                limit=limit, offset=offset, tier=tier, model=model,
                start_date=start_date, end_date=end_date,
                cost_min=cost_min, cost_max=cost_max,
            )
        except CostDashboardError as e:
            raise HTTPException(status_code=400, detail=f"{e.code}: {e.args[0]}")

    @app.get("/api/v1/cost/task/{task_id}")
    async def get_task_detail(task_id: str, token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("task_detail")
        if _dashboard_service is None:
            raise HTTPException(status_code=500, detail="CD-001: Cost dashboard service not initialized")
        result = await _dashboard_service.get_task_detail(task_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"CD-002: No cost data for task_id {task_id}")
        return result

    @app.get("/api/v1/cost/session/{session_id}")
    async def get_session(session_id: str, token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("session")
        if _dashboard_service is None:
            raise HTTPException(status_code=500, detail="CD-001: Cost dashboard service not initialized")
        result = await _dashboard_service.get_session(session_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"CD-003: No session found for session_id {session_id}")
        return result

    @app.get("/api/v1/cost/tiers")
    async def get_tiers(token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("tiers")
        if _dashboard_service is None:
            raise HTTPException(status_code=500, detail="CD-001: Cost dashboard service not initialized")
        return await _dashboard_service.get_tier_breakdown()

    @app.get("/api/v1/cost/models")
    async def get_models(token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("models")
        if _dashboard_service is None:
            raise HTTPException(status_code=500, detail="CD-001: Cost dashboard service not initialized")
        return await _dashboard_service.get_model_breakdown()

    @app.get("/api/v1/etd")
    async def get_etd_list(token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("etd")
        if _dashboard_service is None:
            raise HTTPException(status_code=500, detail="CD-001: Cost dashboard service not initialized")
        return await _dashboard_service.get_etd_list()

    @app.get("/api/v1/audit/log")
    async def get_audit_log(
        token: str = Query(""),
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
        task_id: str | None = Query(None),
        model: str | None = Query(None),
        start_date: str | None = Query(None),
        end_date: str | None = Query(None),
        cost_min: float | None = Query(None, ge=0),
        cost_max: float | None = Query(None, ge=0),
    ):
        _check_auth(token)
        _check_rate_limit("audit")
        if _dashboard_service is None:
            raise HTTPException(status_code=500, detail="CD-001: Cost dashboard service not initialized")
        return await _dashboard_service.get_audit_log(
            limit=limit, offset=offset, task_id=task_id, model=model,
            start_date=start_date, end_date=end_date,
            cost_min=cost_min, cost_max=cost_max,
        )

    @app.websocket("/ws/v1/cost/live")
    async def websocket_endpoint(websocket: WebSocket):
        if _ws_handler is None:
            await websocket.close(code=1011, reason="CD-001: Dashboard not initialized")
            return
        await _ws_handler.handle(websocket)

    @app.post("/api/v1/chat")
    async def chat_send(
        request: ChatRequest,
        token: str = Query(""),
    ):
        _check_auth(token)
        _check_rate_limit("chat")
        if not request.message.strip():
            raise HTTPException(status_code=422, detail="Message cannot be empty")
        if len(request.message) > 10000:
            raise HTTPException(status_code=422, detail="Message too long")
        if _chat_handler is None:
            raise HTTPException(status_code=501, detail="Chat handler not available")
        return await _chat_handler.send_message(
            message=request.message, 
            model=request.model, 
            conversation_id=request.conversation_id,
            images=request.images,
            mode=request.mode,
            search_enabled=request.search_enabled,
            search_sources=request.search_sources
        )

    @app.post("/api/v1/chat/stream")
    async def chat_stream_send(
        request: ChatRequest,
        token: str = Query(""),
    ):
        _check_auth(token)
        _check_rate_limit("chat")
        if not request.message.strip():
            raise HTTPException(status_code=422, detail="Message cannot be empty")
        if len(request.message) > 10000:
            raise HTTPException(status_code=422, detail="Message too long")
        if _chat_handler is None:
            raise HTTPException(status_code=501, detail="Chat handler not available")
        
        return StreamingResponse(
            _chat_handler.stream_message(
                message=request.message, 
                model=request.model, 
                conversation_id=request.conversation_id,
                images=request.images,
                mode=request.mode,
                search_enabled=request.search_enabled,
                search_sources=request.search_sources
            ),
            media_type="text/event-stream"
        )

    @app.post("/api/v1/chat/orchestrate")
    async def chat_orchestrate(
        request: ChatRequest,
        token: str = Query(""),
    ):
        _check_auth(token)
        _check_rate_limit("chat")
        if not request.message.strip():
            raise HTTPException(status_code=422, detail="Message cannot be empty")
        if len(request.message) > 10000:
            raise HTTPException(status_code=422, detail="Message too long")

        conversation_id = request.conversation_id or "conv_" + uuid4().hex

        if _memory_manager is None or _orchestrator is None:
            raise HTTPException(status_code=501, detail="Orchestrator not initialized")

        state = await _memory_manager.get_or_create_board(conversation_id)

        # Inject research context when search is enabled
        user_message = request.message
        preferred = "auto"
        _has_cloud = _secret_registry is not None and bool(
            _secret_registry.get_secret("openrouter_api_key") or
            _secret_registry.get_secret("groq_api_key") or
            os.environ.get("NEXUS_OPENROUTER_API_KEY") or
            os.environ.get("NEXUS_BYOK_API_KEY")
        )
        if not request.model:
            from nexus_r.routing import route_query
            _route_decision = route_query(request.message, has_cloud=_has_cloud)
            if _route_decision.kind == "byok":
                preferred = "byok"
        else:
            from nexus_r.routing import RouteDecision
            preferred = request.model
            _q = request.model.lower()
            if "ollama/" in _q:
                _route_decision = RouteDecision("T1", "local", 0.001, f"User selected {request.model}")
            elif "groq/" in _q:
                _route_decision = RouteDecision("T3", "byok", 0.02, f"User selected {request.model}")
            elif "/" in _q:
                _route_decision = RouteDecision("T4", "byok", 0.10, f"User selected {request.model}")
            else:
                _route_decision = RouteDecision("T1", "local", 0.001, f"User selected {request.model}")
        research_sources: list[tuple[str, str, str]] = []
        if request.search_enabled and request.mode != "speed" and _chat_handler is not None:
            try:
                research_engine = getattr(_chat_handler, "research_engine", None)
                if research_engine is not None:
                    from dataclasses import dataclass
                    @dataclass
                    class _MiniIntent:
                        raw_input: str
                    mini_intent = _MiniIntent(raw_input=request.message)
                    research = await research_engine.run(mini_intent, request.mode, request.search_sources or ["web"])
                    research_sources = research.sources or []
                    if research.context_for_prompt:
                        user_message = f"[Research Context]\n{research.context_for_prompt}\n\n{request.message}"
            except Exception:
                pass

        is_new_conv = not request.conversation_id
        msg_id = str(uuid4())

        async def _orchestrate_stream():
            import json
            from datetime import datetime, timezone
            try:
                # Emit search sources before status events
                if research_sources:
                    sources_payload = [{'title': t, 'url': u, 'content': s} for t, u, s in research_sources]
                    yield f"data: {json.dumps({'type': 'sources', 'data': sources_payload})}\n\n"

                yield f"data: {json.dumps({'type': 'status', 'value': 'routing'})}\n\n"
                yield f"data: {json.dumps({'type': 'status', 'value': 'thinking'})}\n\n"

                started = datetime.now(timezone.utc)
                last_model = ""
                full_text = ""
                reasoning_tokens: int | None = None

                async for chunk in _orchestrator.execute_turn_stream(
                    user_input=user_message,
                    state=state,
                    preferred=preferred,
                ):
                    if chunk.text:
                        full_text += chunk.text
                        yield f"data: {json.dumps({'type': 'token', 'content': chunk.text})}\n\n"
                    if chunk.reasoning_tokens:
                        yield f"data: {json.dumps({'type': 'reasoning', 'content': chunk.text})}\n\n"
                        reasoning_tokens = chunk.reasoning_tokens
                    if chunk.model_name:
                        last_model = chunk.model_name

                latency_ms = (datetime.now(timezone.utc) - started).total_seconds() * 1000
                model_name = last_model or state.last_model_used or ""
                provider = model_name.split("/")[0] if "/" in model_name else "ollama"
                route_tier = _route_decision.tier if _route_decision is not None else "T1"
                route_cost = _route_decision.cost if _route_decision is not None else 0.001
                metadata = {
                    "model": model_name,
                    "provider": provider,
                    "route": route_tier,
                    "latency_ms": latency_ms,
                    "cost": route_cost,
                }
                if reasoning_tokens is not None:
                    metadata["reasoning_tokens"] = reasoning_tokens

                # Emit router decision widget so frontend shows the model/tier/cost card
                yield f"data: {json.dumps({'type': 'widget', 'widget_type': 'router_decision', 'data': {'model': model_name, 'tier': route_tier, 'estimated_cost': route_cost}, 'title': 'Router Decision'})}\n\n"

                # Persist conversation to event store
                if _chat_handler is not None and hasattr(_chat_handler, 'event_store'):
                    ts = datetime.now(timezone.utc).isoformat()
                    if is_new_conv:
                        await _chat_handler.event_store.append(Event(
                            event_type="conversation_created",
                            data={
                                "conversation_id": conversation_id,
                                "title": request.message[:80],
                                "created_at": ts,
                                "message_count": 0,
                            },
                        ))
                    await _chat_handler.event_store.append(Event(
                        event_type="chat_message_sent",
                        data={
                            "message_id": msg_id,
                            "conversation_id": conversation_id,
                            "content": request.message,
                            "model": model_name,
                            "timestamp": ts,
                        },
                    ))
                    await _chat_handler.event_store.append(Event(
                        event_type="chat_message_received",
                        data={
                            "message_id": msg_id,
                            "parent_message_id": msg_id,
                            "conversation_id": conversation_id,
                            "content": full_text,
                            "role": "assistant",
                            "model": model_name,
                            "cost": 0.0,
                            "latency_ms": latency_ms,
                            "timestamp": ts,
                            "blocked": False,
                            "widgets": [],
                        },
                    ))

                yield f"data: {json.dumps({'type': 'done', 'model': model_name, 'metadata': metadata, 'conversation_id': conversation_id})}\n\n"
            except Exception as exc:
                yield f"data: {json.dumps({'type': 'error', 'detail': str(exc)})}\n\n"

        return StreamingResponse(_orchestrate_stream(), media_type="text/event-stream")

    @app.post("/api/v1/chat/hitl-resume")
    async def chat_hitl_resume(
        request: HITLResumeRequest,
        token: str = Query(""),
    ):
        _check_auth(token)
        if _chat_handler is None:
            raise HTTPException(status_code=501, detail="Chat handler not available")
        success = await _chat_handler.resume_hitl(
            message_id=request.message_id,
            code=request.code,
            solved=request.solved
        )
        return {"success": success}

    @app.post("/api/v1/chat/messages/{message_id}/feedback")
    async def chat_message_feedback(
        message_id: str,
        request: FeedbackRequest,
        conversation_id: str = Query(...),
        token: str = Query(""),
    ):
        _check_auth(token)
        _check_rate_limit("message_feedback")
        if _chat_handler is None:
            raise HTTPException(status_code=501, detail="Chat handler not available")
        success = await _chat_handler.record_message_feedback(
            conversation_id=conversation_id,
            message_id=message_id,
            feedback=request.feedback
        )
        if not success:
            raise HTTPException(status_code=404, detail="Message not found")
        return {"success": success}

    @app.post("/api/v1/chat/suggestions")
    async def chat_suggestions(
        request: SuggestionRequest,
        token: str = Query(""),
    ):
        _check_auth(token)
        _check_rate_limit("suggestions")
        if _chat_handler is None:
            raise HTTPException(status_code=501, detail="Chat handler not available")
        normalized = _chat_handler.validate_suggestion(request.prefix, request.limit)
        try:
            suggestions = await asyncio.wait_for(
                _chat_handler.suggestion_registry.suggest(
                    prefix=normalized,
                    limit=request.limit,
                ),
                timeout=3.0,
            )
        except asyncio.TimeoutError:
            raise HTTPException(status_code=504, detail="Suggestion service timed out")
        return {"suggestions": suggestions}

    from fastapi import UploadFile, File
    from .file_parser import extract_file_content
    @app.post("/api/v1/files/extract")
    async def files_extract(
        token: str = Query(""),
        file: UploadFile = File(...)
    ):
        _check_auth(token)
        text = await extract_file_content(file)
        return {"filename": file.filename, "text": text}

    @app.get("/api/v1/chat/conversations")
    async def chat_conversations(
        token: str = Query(""),
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
    ):
        _check_auth(token)
        _check_rate_limit("conversations")
        if _chat_handler is None:
            raise HTTPException(status_code=501, detail="Chat handler not available")
        results = await _chat_handler.get_conversations(limit=limit, offset=offset)
        formatted_results = [
            {
                "id": c.get("conversation_id", ""),
                "title": c.get("title", ""),
                "updated_at": c.get("created_at", ""),
            }
            for c in results
        ]
        return {"conversations": formatted_results}

    @app.get("/api/v1/chat/history")
    async def chat_history(
        token: str = Query(""),
        conversation_id: str | None = Query(None),
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
    ):
        _check_auth(token)
        _check_rate_limit("history")
        if _chat_handler is None:
            raise HTTPException(status_code=501, detail="Chat handler not available")
        results = await _chat_handler.get_history(
            conversation_id=conversation_id, limit=limit, offset=offset
        )
        return {"messages": results}

    @app.post("/api/v1/chat/conversations/{conversation_id}/truncate")
    async def chat_truncate_conversation(conversation_id: str, request: TruncateRequest, token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("truncate_conversation")
        if _chat_handler is None:
            raise HTTPException(status_code=501, detail="Chat handler not available")
        success = await _chat_handler.truncate_conversation(conversation_id, request.message_id, request.keep_inclusive)
        if not success:
            raise HTTPException(status_code=404, detail="Message not found")
        return {"success": success}

    @app.delete("/api/v1/chat/conversations/{conversation_id}")
    async def chat_delete_conversation(conversation_id: str, token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("delete_conversation")
        if _chat_handler is None:
            raise HTTPException(status_code=501, detail="Chat handler not available")
        success = await _chat_handler.delete_conversation(conversation_id)
        return {"success": success}

    @app.post("/api/v1/chat/clear-all")
    async def chat_clear_all(token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("clear_all")
        if _chat_handler is None:
            raise HTTPException(status_code=501, detail="Chat handler not available")
        success = await _chat_handler.clear_all_conversations()
        return {"success": success}

    # --- Projects ---

    @app.get("/api/v1/projects")
    async def projects_list(token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("projects_list")
        if _chat_handler is None:
            raise HTTPException(status_code=501, detail="Chat handler not available")
        projects = await _chat_handler.get_projects()
        return {"projects": projects}

    @app.post("/api/v1/projects")
    async def projects_create(req: dict[str, Any], token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("projects_create")
        if _chat_handler is None:
            raise HTTPException(status_code=501, detail="Chat handler not available")
        project = await _chat_handler.create_project(name=req.get("name", ""), description=req.get("description", ""))
        return project

    @app.put("/api/v1/projects/{project_id}")
    async def projects_update(project_id: str, req: dict[str, Any], token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("projects_update")
        if _chat_handler is None:
            raise HTTPException(status_code=501, detail="Chat handler not available")
        success = await _chat_handler.update_project(project_id, name=req.get("name"), description=req.get("description"))
        return {"success": success}

    @app.delete("/api/v1/projects/{project_id}")
    async def projects_delete(project_id: str, token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("projects_delete")
        if _chat_handler is None:
            raise HTTPException(status_code=501, detail="Chat handler not available")
        success = await _chat_handler.delete_project(project_id)
        return {"success": success}

    @app.post("/api/v1/projects/{project_id}/conversations")
    async def projects_add_conversation(project_id: str, req: dict[str, Any], token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("projects_add_conv")
        if _chat_handler is None:
            raise HTTPException(status_code=501, detail="Chat handler not available")
        success = await _chat_handler.add_conversation_to_project(project_id, req.get("conversation_id", ""))
        return {"success": success}

    @app.delete("/api/v1/projects/{project_id}/conversations/{conversation_id}")
    async def projects_remove_conversation(project_id: str, conversation_id: str, token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("projects_remove_conv")
        if _chat_handler is None:
            raise HTTPException(status_code=501, detail="Chat handler not available")
        success = await _chat_handler.remove_conversation_from_project(project_id, conversation_id)
        return {"success": success}

    @app.get("/api/v1/chat/message/{message_id}")
    async def chat_message(
        message_id: str,
        token: str = Query(""),
    ):
        _check_auth(token)
        _check_rate_limit("message")
        if _chat_handler is None:
            raise HTTPException(status_code=501, detail="Chat handler not available")
        res = await _chat_handler.get_message(message_id)
        if res is None:
            raise HTTPException(status_code=404, detail="Message not found")
        return res

    @app.post("/api/v1/chat/interrupt")
    async def chat_interrupt(
        token: str = Query(""),
        message_id: str = Query(...),
    ):
        _check_auth(token)
        _check_rate_limit("interrupt")
        if _chat_handler is None:
            raise HTTPException(status_code=501, detail="Chat handler not available")
        success = await _chat_handler.interrupt_message(message_id)
        return {"success": success}

    # --- Model Configuration and Management Endpoints ---

    @app.get("/api/v1/models/status")
    async def models_status(token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("models_status")
        if _model_manager is None:
            raise HTTPException(status_code=500, detail="Model manager not initialized")
        
        cfg = _model_manager.config
        api_key_configured = False
        cloud_provider = "none"
        local_model = cfg.models.local_model
        
        saved = _model_manager.load_saved_config()
        if saved:
            local_model = saved.get("local_model", local_model)
            cloud_provider = saved.get("cloud_provider", "none")
            if saved.get("api_key"):
                api_key_configured = True
        else:
            from modules.cognition_router.src.model_manager import CLOUD_PROVIDER_OPTIONS
            for opt in CLOUD_PROVIDER_OPTIONS:
                if opt["value"] != "none":
                    if os.environ.get(opt["env_var"]) or (_secret_registry and _secret_registry.get_secret(opt["secret_name"])):
                        cloud_provider = opt["value"]
                        api_key_configured = True
                        break
        
        current = {
            "local_model": local_model,
            "cloud_provider": cloud_provider,
            "api_key_configured": api_key_configured,
        }
        
        from modules.cognition_router.src.model_manager import CLOUD_PROVIDER_OPTIONS
        filtered_options = []
        for opt in CLOUD_PROVIDER_OPTIONS:
            if opt["value"] == "none":
                filtered_options.append(opt)
                continue
            if os.environ.get(opt["env_var"]) or (_secret_registry and _secret_registry.get_secret(opt["secret_name"])):
                filtered_options.append({**opt, "api_key_configured": True})
        return {
            "current": current,
            "cloud_options": filtered_options,
        }

    @app.get("/api/v1/models/routing-profile")
    async def models_routing_profile(token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("models_routing_profile")
        if _chat_handler is None or _chat_handler.router is None:
            raise HTTPException(status_code=500, detail="Router not available")
            
        registry = getattr(_chat_handler.router, "models", None)
        if registry is None:
            raise HTTPException(status_code=500, detail="Model registry not available")
            
        categories = getattr(registry, "_semantic_categories", {})
        
        return {
            "router": "Semantic Router v1",
            "reasoning": categories.get("math_reasoning", {}).get("default_model", "Unknown"),
            "coding": categories.get("coding", {}).get("default_model", "Unknown"),
            "general": categories.get("creative", {}).get("default_model", "Unknown"),
            "embedding": "nomic-embed-text:latest"
        }

    @app.get("/api/v1/models/list-local")
    async def models_list_local(token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("models_list_local")
        if _model_manager is None:
            raise HTTPException(status_code=500, detail="Model manager not initialized")
        return await _model_manager.list_all_local_models()

    @app.get("/api/v1/models/download-jobs")
    async def models_download_jobs(token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("models_download_jobs")
        if _model_manager is None:
            raise HTTPException(status_code=500, detail="Model manager not initialized")
        jobs = _model_manager.get_active_jobs()
        return {"jobs": jobs}

    @app.get("/api/v1/models/download-status/{job_id}")
    async def models_download_status(job_id: str, token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("models_download_status")
        if _model_manager is None:
            raise HTTPException(status_code=500, detail="Model manager not initialized")
        status = _model_manager.get_download_status(job_id)
        if status is None:
            raise HTTPException(status_code=404, detail="Download job not found")
        return status

    @app.get("/api/v1/models/ollama-status/{model_name:path}")
    async def models_ollama_status(model_name: str, token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("models_ollama_status")
        if _model_manager is None:
            raise HTTPException(status_code=500, detail="Model manager not initialized")
        return await _model_manager.check_model_status(model_name)

    @app.post("/api/v1/models/download")
    async def models_download(req: DownloadRequest, token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("models")
        if _model_manager is None:
            raise HTTPException(status_code=500, detail="Model manager not initialized")
        return _model_manager.start_download(req.model_name, url=getattr(req, 'url', ''))

    @app.get("/api/v1/models/hf/search")
    async def models_hf_search(
        token: str = Query(""),
        query: str = Query(""),
        filter_tag: str = Query(""),
        sort: str = Query("downloads"),
        limit: int = Query(20, ge=1, le=100)
    ):
        _check_auth(token)
        _check_rate_limit("models")
        if _model_manager is None:
            raise HTTPException(status_code=501, detail="Model manager not available")
        results = await _model_manager.hf_client.search_models(query, filter_tag, sort, limit)
        return {"results": results}

    @app.get("/api/v1/models/openrouter/list")
    async def models_openrouter_list(token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("models")
        if _model_manager is None:
            raise HTTPException(status_code=501, detail="Model manager not available")
        results = await _model_manager.openrouter_client.list_models()
        return {"results": results}

    @app.post("/api/v1/models/download-pause/{job_id}")
    async def models_download_pause(job_id: str, token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("models")
        if _model_manager is None:
            raise HTTPException(status_code=501, detail="Model manager not available")
        success = _model_manager.pause_download(job_id)
        return {"success": success}

    @app.post("/api/v1/models/download-resume/{job_id}")
    async def models_download_resume(job_id: str, token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("models")
        if _model_manager is None:
            raise HTTPException(status_code=501, detail="Model manager not available")
        success = _model_manager.resume_download(job_id)
        return {"success": success}


    @app.post("/api/v1/models/delete")
    async def models_delete(req: DeleteRequest, token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("models")
        if _model_manager is None:
            raise HTTPException(status_code=501, detail="Model manager not available")
        success = await _model_manager.delete_local_model(req.model_name)
        return {"success": success}

    @app.post("/api/v1/models/download-cancel/{job_id}")
    async def models_download_cancel(job_id: str, token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("models_download_cancel")
        if _model_manager is None:
            raise HTTPException(status_code=500, detail="Model manager not initialized")
        return _model_manager.cancel_download(job_id)

    @app.post("/api/v1/models/test")
    async def models_test(req: TestRequest, token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("models_test")
        if _model_manager is None:
            raise HTTPException(status_code=500, detail="Model manager not initialized")
        
        if req.local_model:
            return await _model_manager.test_local_model(req.local_model)
        elif req.cloud_provider:
            return await _model_manager.test_cloud_connection(req.cloud_provider, req.api_key or "")
        else:
            raise HTTPException(status_code=422, detail="Either local_model or cloud_provider must be provided")

    @app.get("/api/v1/models/config")
    async def models_get_config(token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("models_get_config")
        if _model_manager is None or _chat_handler is None or _chat_handler.router is None:
            raise HTTPException(status_code=500, detail="Components not initialized")
        
        cfg = _model_manager.config
        api_key_configured = False
        cloud_provider = "none"
        local_model = cfg.models.local_model
        
        saved = _model_manager.load_saved_config()
        if saved:
            local_model = saved.get("local_model", local_model)
            cloud_provider = saved.get("cloud_provider", "none")
            if saved.get("api_key"):
                api_key_configured = True
        else:
            from modules.cognition_router.src.model_manager import CLOUD_PROVIDER_OPTIONS
            byok_model = cfg.models.byok_model
            for opt in CLOUD_PROVIDER_OPTIONS:
                # If there's an api key, assume it's configured
                if os.environ.get(opt["env_var"]):
                    cloud_provider = opt["value"]
                    api_key_configured = True
                    break
        
        registry = getattr(_chat_handler.router, "models", None)
        categories = getattr(registry, "_semantic_categories", {}) if registry else {}
        routingProfile = saved.get("routingProfile") or {
            "router": "Semantic Router v1",
            "reasoning": categories.get("math_reasoning", {}).get("default_model", "Unknown"),
            "coding": categories.get("coding", {}).get("default_model", "Unknown"),
            "general": categories.get("creative", {}).get("default_model", "Unknown"),
            "embedding": "nomic-embed-text:latest"
        }

        return {
            "current": {
                "local_model": local_model,
                "cloud_provider": cloud_provider,
                "api_key_configured": api_key_configured,
            },
            "routingProfile": routingProfile
        }

    @app.post("/api/v1/models/config")
    async def models_post_config(req: ConfigRequest, token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("models_post_config")
        if _model_manager is None:
            raise HTTPException(status_code=500, detail="Model manager not initialized")
        
        # We reuse configure but add routingProfile to it
        result = await _model_manager.configure(
            local_model=req.local_model,
            cloud_provider=req.cloud_provider,
            api_key=req.api_key,
            routing_profile=req.routingProfile.model_dump() if req.routingProfile else None
        )
        return result

    @app.post("/api/v1/models/configure")
    async def models_configure(req: ConfigureRequest, token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("models_configure")
        if _model_manager is None:
            raise HTTPException(status_code=500, detail="Model manager not initialized")
        
        return await _model_manager.configure(
            local_model=req.local_model,
            cloud_provider=req.cloud_provider,
            api_key=req.api_key,
        )

    # --- Providers Configuration Endpoints ---

    class ProviderRequest(BaseModel):
        provider: str
        api_key: str | None = None

    @app.get("/api/v1/providers")
    async def get_providers(token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("providers")
        if _secret_registry is None:
            raise HTTPException(status_code=500, detail="Secret registry not initialized")
            
        from modules.cognition_router.src.model_manager import CLOUD_PROVIDER_OPTIONS
        
        results = []
        for opt in CLOUD_PROVIDER_OPTIONS:
            if opt["value"] == "none":
                continue
            
            # Check if API key is stored (we just check if it exists or check the env var)
            has_key = bool(_secret_registry.get_secret(opt["secret_name"]) or os.environ.get(opt["env_var"]))
            
            results.append({
                "id": opt["value"],
                "name": opt["label"].split(" (")[0],  # Extract just the name
                "has_key": has_key,
                "status": "Active" if has_key else "Inactive",
                "key_prefix": opt["key_prefix"],
                "base_url": opt.get("base_url", ""),
            })
            
        return {"providers": results}

    @app.get("/api/v1/providers/{provider}/models")
    async def get_provider_models(provider: str, token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("provider_models")
        if _model_manager is None:
            raise HTTPException(status_code=500, detail="Model manager not initialized")
            
        models = await _model_manager.list_cloud_models(provider)
        return {"models": models}

    @app.post("/api/v1/providers")
    async def update_provider(req: ProviderRequest, token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("update_provider")
        if _secret_registry is None:
            raise HTTPException(status_code=500, detail="Secret registry not initialized")
            
        from modules.cognition_router.src.model_manager import CLOUD_PROVIDER_OPTIONS
        opt = next((p for p in CLOUD_PROVIDER_OPTIONS if p["value"] == req.provider), None)
        
        if not opt:
            raise HTTPException(status_code=404, detail="Provider not found")
            
        if req.api_key:
            _secret_registry.set_secret(opt["secret_name"], req.api_key)
            os.environ[opt["env_var"]] = req.api_key
            
        return {"success": True, "provider": req.provider}

    @app.delete("/api/v1/providers/{provider}")
    async def delete_provider(provider: str, token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("delete_provider")
        if _secret_registry is None:
            raise HTTPException(status_code=500, detail="Secret registry not initialized")
            
        from modules.cognition_router.src.model_manager import CLOUD_PROVIDER_OPTIONS
        opt = next((p for p in CLOUD_PROVIDER_OPTIONS if p["value"] == provider), None)
        
        if not opt:
            raise HTTPException(status_code=404, detail="Provider not found")
            
        _secret_registry.delete_secret(opt["secret_name"])
        if opt["env_var"] in os.environ:
            del os.environ[opt["env_var"]]
            
        return {"success": True, "provider": provider}

    # --- Tools API ---
    @app.get("/api/v1/tools")
    async def get_tools(token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("tools")
        
        # Static capability mapping representing the exact capabilities 
        # implemented in execution_sandbox and chat_handler
        return {
            "tools": [
                {
                    "id": "playwright_search",
                    "name": "Browser Sandbox",
                    "description": "Headless agentic browser capable of web search, navigation, clicking, and scraping.",
                    "category": "External",
                    "status": "Active"
                },
                {
                    "id": "timesfm_forecaster",
                    "name": "TimesFM Forecaster",
                    "description": "Zero-shot time-series forecaster for predicting sequence trends and bounds.",
                    "category": "Cognitive",
                    "status": "Active"
                },
                {
                    "id": "safe_calculator",
                    "name": "Safe Math Evaluator",
                    "description": "Sandboxed calculator for evaluating strict mathematical expressions instantly.",
                    "category": "Execution",
                    "status": "Active"
                },
                {
                    "id": "memory_parser",
                    "name": "Preference Engine",
                    "description": "Extracts semantic episodic memories and manages explicit user preferences.",
                    "category": "Cognitive",
                    "status": "Active"
                },
                {
                    "id": "file_operations",
                    "name": "Local Filesystem",
                    "description": "Allows the agent to read, write, and list files within the restricted workspace.",
                    "category": "Execution",
                    "status": "Active"
                },
                {
                    "id": "terminal_sandbox",
                    "name": "Terminal Access",
                    "description": "Execute whitelisted shell commands (e.g., git, python, npm) safely.",
                    "category": "Execution",
                    "status": "Active"
                }
            ]
        }

    # --- Browser Tools API ---
    @app.get("/api/v1/tools/browser/status")
    async def browser_status(token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("tools")
        if _chat_handler is None or not hasattr(_chat_handler, "browser"):
            return {"started": False, "headless": True, "current_url": None}
        b = _chat_handler.browser
        started = b._page is not None
        url = b._page.url if started else None
        return {
            "started": started,
            "headless": b.headless,
            "current_url": url,
        }

    @app.post("/api/v1/tools/browser/start")
    async def browser_start(token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("tools")
        if _chat_handler is None or not hasattr(_chat_handler, "browser"):
            raise HTTPException(status_code=503, detail="Chat handler not initialized")
        try:
            await _chat_handler.browser.start()
            return {"success": True}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/v1/tools/browser/stop")
    async def browser_stop(token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("tools")
        if _chat_handler is None or not hasattr(_chat_handler, "browser"):
            raise HTTPException(status_code=503, detail="Chat handler not initialized")
        try:
            await _chat_handler.browser.stop()
            return {"success": True}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/v1/tools/browser/page-text")
    async def browser_page_text(token: str = Query(""), max_chars: int = Query(4000, le=20000)):
        _check_auth(token)
        _check_rate_limit("tools")
        if _chat_handler is None or not hasattr(_chat_handler, "browser"):
            raise HTTPException(status_code=503, detail="Chat handler not initialized")
        try:
            text = await _chat_handler.browser.extract_text(max_chars=max_chars)
            return {"success": True, "text": text}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/v1/tools/browser/screenshot")
    async def browser_screenshot(token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("tools")
        if _chat_handler is None or not hasattr(_chat_handler, "browser"):
            raise HTTPException(status_code=503, detail="Chat handler not initialized")
        try:
            img_bytes = await _chat_handler.browser.screenshot()
            if img_bytes is None:
                raise HTTPException(status_code=500, detail="Screenshot failed")
            import base64
            return {"success": True, "image_base64": base64.b64encode(img_bytes).decode("utf-8")}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/v1/tools/browser/switch-headed")
    async def browser_switch_headed(token: str = Query("")):
        _check_auth(token)
        _check_rate_limit("tools")
        if _chat_handler is None or not hasattr(_chat_handler, "browser"):
            raise HTTPException(status_code=503, detail="Chat handler not initialized")
        try:
            result = await _chat_handler.browser.switch_to_headed()
            return {"success": result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/v1/tools/browser/save-session")
    async def browser_save_session(token: str = Query(""), path: str = Query("")):
        _check_auth(token)
        _check_rate_limit("tools")
        if _chat_handler is None or not hasattr(_chat_handler, "browser"):
            raise HTTPException(status_code=503, detail="Chat handler not initialized")
        try:
            file_path = path or os.path.join(os.path.dirname(__file__), "browser_session.json")
            result = await _chat_handler.browser.save_session_state(file_path)
            return {"success": result, "path": file_path}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/v1/tools/browser/load-session")
    async def browser_load_session(token: str = Query(""), path: str = Query("")):
        _check_auth(token)
        _check_rate_limit("tools")
        if _chat_handler is None or not hasattr(_chat_handler, "browser"):
            raise HTTPException(status_code=503, detail="Chat handler not initialized")
        try:
            file_path = path or os.path.join(os.path.dirname(__file__), "browser_session.json")
            result = await _chat_handler.browser.load_session_state(file_path)
            return {"success": result is not None}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/v1/tools/browser/network-data")
    async def browser_network_data(token: str = Query(""), max_entries: int = Query(20, le=50)):
        _check_auth(token)
        _check_rate_limit("tools")
        if _chat_handler is None or not hasattr(_chat_handler, "browser"):
            raise HTTPException(status_code=503, detail="Chat handler not initialized")
        try:
            data = _chat_handler.browser.read_network_data(max_entries=max_entries)
            return {"success": True, "entries": data, "count": len(data)}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/{full_path:path}")
    async def catch_all(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("static/"):
            raise HTTPException(status_code=404, detail="Not Found")
        return HTMLResponse(content=index_html(), status_code=200)

    return app

def index_html() -> str:
    static_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.isfile(static_path):
        with open(static_path, encoding="utf-8") as f:
            content = f.read()
            token = _get_token()
            meta_tag = f'<meta name="nexus-token" content="{token}">'
            if "<head>" in content:
                content = content.replace("<head>", f"<head>\n    {meta_tag}")
            return content
    return "<html><body><h1>NEXUS-R Cost Dashboard</h1><p>Static files not found.</p></body></html>"


def _check_auth(token: str) -> None:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide ?token=xxx or Authorization: Bearer header.",
        )
    if token != _get_token():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid authentication token.",
        )


def _check_rate_limit(endpoint: str) -> None:
    global _rate_limiter
    now = time.monotonic()
    key = endpoint
    timestamps = _rate_limiter[key]
    cutoff = now - RATE_LIMIT_WINDOW
    timestamps[:] = [t for t in timestamps if t > cutoff]
    if len(timestamps) >= RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": str(RATE_LIMIT_WINDOW)},
            detail=f"Rate limit exceeded. Max {RATE_LIMIT_MAX} requests per {RATE_LIMIT_WINDOW}s.",
        )
    timestamps.append(now)


def get_ws_handler() -> CostWebSocketHandler | None:
    return _ws_handler
