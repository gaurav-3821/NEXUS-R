from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from enum import Enum
import json
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

import aiosqlite
from pydantic import BaseModel, Field

from .errors import StateStoreError
from .telemetry import RuntimeTelemetry


class PermissionTier(str, Enum):
    T1 = "T1"
    T2 = "T2"
    T3 = "T3"
    T4 = "T4"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Event(BaseModel):
    event_type: str
    data: dict[str, Any]
    id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=utc_now)
    parent_event_id: str | None = None
    embedding: list[float] | None = None

    def to_record(self) -> dict[str, Any]:
        record = self.model_dump(mode="json")
        record["timestamp"] = self.timestamp.isoformat()
        return record


class CausalEvent(Event):
    verification_result: str = "unknown"
    model_used: str = "none"
    cost: float = 0.0
    tier: PermissionTier = PermissionTier.T1


class Action(BaseModel):
    name: str
    tier: PermissionTier
    target: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskDefinition(BaseModel):
    raw_input: str
    action_type: str
    parameters: dict[str, Any]
    tier: PermissionTier
    task_id: str = Field(default_factory=lambda: str(uuid4()))


class IntentResult(BaseModel):
    raw_input: str
    normalized_input: str
    task_type: str
    complexity: float
    confidence: float
    parameters: dict[str, Any]
    suggested_tier: PermissionTier
    warnings: list[str] = Field(default_factory=list)


class RoutingDecision(BaseModel):
    selected_model: str
    selected_tier: PermissionTier
    cost_estimate: float
    rationale: str
    etd_match_found: bool
    fallback_chain: list[str] = Field(default_factory=list)
    car_tier: int = 0
    car_tier_name: str = "local_7b"
    parallel_probe_used: bool = False
    de_escalated: bool = False
    requires_approval: bool = False


class ExecutionResult(BaseModel):
    success: bool
    message: str
    output: Any = None
    error: str | None = None
    command: str | None = None
    artifacts: list[str] = Field(default_factory=list)
    cost_incurred: float = 0.0


class PermissionDecision(BaseModel):
    allowed: bool
    tier: PermissionTier
    reason: str
    redacted_metadata: dict[str, Any] = Field(default_factory=dict)


class EventStore:
    def __init__(self, db_path: str | Path, telemetry: RuntimeTelemetry | None = None, cache_size_mb: int = 50) -> None:
        self.db_path = str(Path(db_path))
        self.telemetry = telemetry
        self._cache_size_mb = max(1, min(500, cache_size_mb))
        self._initialized = False
        self._init_lock = asyncio.Lock()
        self._write_lock = asyncio.Lock()
        self._read_lock = asyncio.Lock()
        self._write_db: aiosqlite.Connection | None = None
        self._read_db: aiosqlite.Connection | None = None
        self._append_queue: asyncio.Queue[tuple[Event, asyncio.Future[str]] | None] | None = None
        self._writer_task: asyncio.Task[None] | None = None

    async def initialize(self) -> None:
        if self._initialized:
            return
        async with self._init_lock:
            if self._initialized:
                return
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            if self.telemetry is not None:
                self.telemetry.emit("event_store_initialize", db_path=self.db_path)
            self._write_db = await self._open_connection()
            self._read_db = await self._open_connection()
            self._append_queue = asyncio.Queue()
            self._writer_task = asyncio.create_task(self._flush_loop())
            await self._write_db.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    parent_event_id TEXT,
                    data_json TEXT NOT NULL,
                    embedding_json TEXT,
                    verification_result TEXT,
                    model_used TEXT,
                    cost REAL DEFAULT 0,
                    tier TEXT
                )
                """
            )
            await self._write_db.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)"
            )
            await self._write_db.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)"
            )
            await self._write_db.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_parent ON events(parent_event_id)"
            )
            await self._write_db.commit()
            self._initialized = True

    async def append(self, event: Event) -> str:
        await self.initialize()
        assert self._append_queue is not None
        loop = asyncio.get_running_loop()
        future: asyncio.Future[str] = loop.create_future()
        await self._append_queue.put((event, future))
        return await future

    async def append_many(self, events: list[Event]) -> list[str]:
        await self.initialize()
        return await self._write_events(events)

    async def _write_events(self, events: list[Event]) -> list[str]:
        assert self._write_db is not None
        started = perf_counter()
        rows = [
            (
                event.id,
                event.timestamp.isoformat(),
                event.event_type,
                event.parent_event_id,
                json.dumps(event.data, default=str),
                json.dumps(event.embedding) if event.embedding is not None else None,
                getattr(event, "verification_result", None),
                getattr(event, "model_used", None),
                getattr(event, "cost", 0.0),
                getattr(getattr(event, "tier", None), "value", None),
            )
            for event in events
        ]
        try:
            async with self._write_lock:
                await self._write_db.executemany(
                    """
                    INSERT INTO events (
                        id, timestamp, event_type, parent_event_id, data_json,
                        embedding_json, verification_result, model_used, cost, tier
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )
                await self._write_db.commit()
                if self.telemetry is not None:
                    duration_ms = (perf_counter() - started) * 1000
                    self.telemetry.increment("event_store.rows_written_total", len(rows))
                    self.telemetry.increment("event_store.write_batches_total")
                    self.telemetry.set_gauge("event_store.last_batch_size", float(len(rows)))
                    self.telemetry.emit(
                        "event_store_write",
                        batch_size=len(rows),
                        duration_ms=round(duration_ms, 3),
                    )
        except aiosqlite.Error as exc:
            if self.telemetry is not None:
                self.telemetry.increment("event_store.write_failures_total")
                self.telemetry.emit(
                    "event_store_write_failed",
                    batch_size=len(rows),
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
            raise StateStoreError(str(exc)) from exc
        return [event.id for event in events]

    async def _flush_loop(self) -> None:
        assert self._append_queue is not None
        while True:
            item = await self._append_queue.get()
            if item is None:
                self._append_queue.task_done()
                break
            batch: list[tuple[Event, asyncio.Future[str]]] = [item]
            stop_after_batch = False
            while len(batch) < 128:
                try:
                    next_item = self._append_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                if next_item is None:
                    self._append_queue.task_done()
                    stop_after_batch = True
                    break
                batch.append(next_item)
            try:
                await self._write_events([event for event, _future in batch])
            except Exception as exc:
                for _event, future in batch:
                    if not future.done():
                        future.set_exception(exc)
            else:
                for event, future in batch:
                    if not future.done():
                        future.set_result(event.id)
            finally:
                for _event, _future in batch:
                    self._append_queue.task_done()
            if stop_after_batch:
                break

    async def query(self, filters: dict[str, Any] | None = None) -> list[Event]:
        await self.initialize()
        assert self._read_db is not None
        started = perf_counter()
        filters = filters or {}
        clauses: list[str] = []
        values: list[Any] = []
        allowed = {"event_type", "parent_event_id", "id", "tier"}
        for key, value in filters.items():
            if key not in allowed:
                continue
            clauses.append(f"{key} = ?")
            values.append(value.value if hasattr(value, "value") else value)
        sql = "SELECT * FROM events"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY timestamp ASC"
        async with self._read_lock:
            async with self._read_db.execute(sql, values) as cursor:
                rows = await cursor.fetchall()
        if self.telemetry is not None:
            duration_ms = (perf_counter() - started) * 1000
            self.telemetry.increment("event_store.read_queries_total")
            self.telemetry.emit(
                "event_store_query",
                row_count=len(rows),
                duration_ms=round(duration_ms, 3),
                filters=filters,
            )
        return [self._row_to_event(row) for row in rows]

    async def get_chain(self, event_id: str) -> list[Event]:
        await self.initialize()
        assert self._read_db is not None
        started = perf_counter()
        async with self._read_lock:
            async with self._read_db.execute(
                """
                WITH RECURSIVE chain(id, timestamp, event_type, parent_event_id, data_json,
                                     embedding_json, verification_result, model_used, cost, tier, depth) AS (
                    SELECT id, timestamp, event_type, parent_event_id, data_json,
                           embedding_json, verification_result, model_used, cost, tier, 0
                    FROM events
                    WHERE id = ?
                    UNION ALL
                    SELECT e.id, e.timestamp, e.event_type, e.parent_event_id, e.data_json,
                           e.embedding_json, e.verification_result, e.model_used, e.cost, e.tier, c.depth + 1
                    FROM events e
                    JOIN chain c ON e.id = c.parent_event_id
                )
                SELECT id, timestamp, event_type, parent_event_id, data_json,
                       embedding_json, verification_result, model_used, cost, tier
                FROM chain
                ORDER BY depth DESC
                """,
                (event_id,),
            ) as cursor:
                rows = await cursor.fetchall()
        if self.telemetry is not None:
            duration_ms = (perf_counter() - started) * 1000
            self.telemetry.increment("event_store.chain_reads_total")
            self.telemetry.emit(
                "event_store_chain_query",
                event_id=event_id,
                row_count=len(rows),
                duration_ms=round(duration_ms, 3),
            )
        return [self._row_to_event(row) for row in rows]

    async def get_by_time_range(self, start: datetime, end: datetime) -> list[Event]:
        await self.initialize()
        assert self._read_db is not None
        async with self._read_lock:
            async with self._read_db.execute(
                """
                SELECT * FROM events
                WHERE timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp ASC
                """,
                (start.isoformat(), end.isoformat()),
            ) as cursor:
                rows = await cursor.fetchall()
        return [self._row_to_event(row) for row in rows]

    async def get_by_type(self, event_type: str) -> list[Event]:
        return await self.query({"event_type": event_type})

    async def create_projected_view(self, name: str, query: str) -> None:
        await self.initialize()
        assert self._write_db is not None
        safe_name = "".join(ch for ch in name if ch.isalnum() or ch == "_")
        if not safe_name:
            raise StateStoreError("Invalid view name.")
        async with self._write_lock:
            await self._write_db.execute(f"DROP VIEW IF EXISTS {safe_name}")
            await self._write_db.execute(f"CREATE VIEW {safe_name} AS {query}")
            await self._write_db.commit()

    async def compact(self, older_than_days: int) -> int:
        await self.initialize()
        assert self._read_db is not None
        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
        async with self._read_lock:
            async with self._read_db.execute(
                """
                SELECT COUNT(*) AS count FROM events
                WHERE timestamp < ? AND event_type NOT IN ('audit_log', 'task_completed')
                """,
                (cutoff.isoformat(),),
            ) as cursor:
                row = await cursor.fetchone()
        return int(row["count"])

    async def similar_success_exists(self, normalized_input: str) -> bool:
        await self.initialize()
        assert self._read_db is not None
        async with self._read_lock:
            async with self._read_db.execute(
                "SELECT data_json FROM events WHERE event_type = 'task_completed'"
            ) as cursor:
                rows = await cursor.fetchall()
        for row in rows:
            payload = json.loads(row["data_json"])
            if payload.get("normalized_input") == normalized_input and payload.get("success"):
                return True
        return False

    def _row_to_event(self, row: aiosqlite.Row) -> Event:
        payload = json.loads(row["data_json"])
        embedding = json.loads(row["embedding_json"]) if row["embedding_json"] else None
        timestamp = datetime.fromisoformat(row["timestamp"])
        kwargs = {
            "event_type": row["event_type"],
            "data": payload,
            "id": row["id"],
            "timestamp": timestamp,
            "parent_event_id": row["parent_event_id"],
            "embedding": embedding,
        }
        if row["verification_result"] is not None or row["model_used"] is not None:
            tier_value = row["tier"] or PermissionTier.T1.value
            return CausalEvent(
                **kwargs,
                verification_result=row["verification_result"] or "unknown",
                model_used=row["model_used"] or "none",
                cost=float(row["cost"] or 0.0),
                tier=PermissionTier(tier_value),
            )
        return Event(**kwargs)

    async def _open_connection(self) -> aiosqlite.Connection:
        db = await aiosqlite.connect(self.db_path, timeout=5)
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA busy_timeout=5000")
        await db.execute("PRAGMA synchronous=NORMAL")
        await db.execute("PRAGMA temp_store=MEMORY")
        await db.execute(f"PRAGMA cache_size={-self._cache_size_mb * 1024}")
        await db.execute("PRAGMA wal_autocheckpoint=1000")
        return db

    async def close(self) -> None:
        if self._append_queue is not None:
            await self._append_queue.put(None)
            if self._writer_task is not None:
                await self._writer_task
                self._writer_task = None
            self._append_queue = None
        if self._write_db is not None:
            await self._write_db.close()
            self._write_db = None
        if self._read_db is not None:
            await self._read_db.close()
            self._read_db = None
        self._initialized = False
        if self.telemetry is not None:
            self.telemetry.emit("event_store_closed", db_path=self.db_path)
