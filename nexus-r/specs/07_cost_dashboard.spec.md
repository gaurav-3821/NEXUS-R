# Cost Dashboard Phase 2 Specification

## Responsibilities

- Real-time cost visualization per task and cumulative.
- FastAPI backend for querying cost data.
- WebSocket push for live updates during task execution.
- Historical cost aggregation by tier, model, and session.

## Architecture

```
CLI / Browser  ←→  FastAPI (port 8400)  ←→  EventStore (SQLite)
                       ↕
                  WebSocket (port 8401)
                       ↕
              Runtime CostTracker (push)
```

## Backend API (FastAPI)

### Endpoints

```
GET  /api/v1/cost/summary
  → { total_cost, per_tier: {T1: x, T2: y, ...}, per_model: {...} }

GET  /api/v1/cost/tasks?limit=50&offset=0
  → [{ task_id, cost, model, tier, timestamp, action_type }, ...]

GET  /api/v1/cost/task/{task_id}
  → { task_id, total_cost, steps: [{ step, cost, model, tier }] }

GET  /api/v1/cost/session/{session_id}
  → { session_id, total_cost, task_count, first_seen, last_seen }

GET  /api/v1/cost/tiers
  → [{ tier, total_cost, task_count, avg_cost }, ...]

GET  /api/v1/cost/models
  → [{ model, total_cost, task_count, avg_latency_ms }, ...]

GET  /api/v1/dashboard
  → HTML page (server-rendered dashboard, optional)
```

### WebSocket

```
WS /ws/v1/cost/live

Server → Client messages:
  { type: "cost_update", task_id, cost, model, tier, running_total }
  { type: "task_started", task_id, estimated_cost }
  { type: "task_completed", task_id, final_cost, latency_ms }
  { type: "session_reset", total_cost: 0.0 }

Client → Server messages:
  { type: "subscribe", filter: "all" | "tier:T1" | "model:groq/..." }
  { type: "unsubscribe" }
```

## Rate Limit

All API endpoints enforce a **100 requests per minute** limit per client IP.
Exceeding the limit returns HTTP 429 with a `Retry-After` header.
WebSocket connections are exempt but each connection sends no more than
1 message per 100ms (server drops faster messages silently).

## Backend Service

```python
class CostDashboardService:
    def __init__(self, event_store: EventStore):
        self.event_store = event_store

    async def get_summary(self) -> dict[str, object]:
        """
        Aggregate cost from event_store.get_by_type("cost_recorded").
        Returns total_cost, per_tier breakdown, per_model breakdown.
        """

    async def get_tasks(
        self,
        limit: int = 50,
        offset: int = 0,
        tier: str | None = None,
        model: str | None = None,
    ) -> list[dict[str, object]]:
        """
        Paginated task cost list with optional tier/model filter.
        Ordered by timestamp DESC.
        """

    async def get_task_detail(self, task_id: str) -> dict[str, object] | None:
        """
        Single task with per-step cost breakdown.
        Returns None if task_id not found.
        """

    async def get_session(self, session_id: str) -> dict[str, object] | None:
        """
        Aggregate cost for a session (all tasks sharing session_id prefix).
        """

    async def get_tier_breakdown(self) -> list[dict[str, object]]:
        """
        Cost aggregated by tier: total, count, avg.
        """

    async def get_model_breakdown(self) -> list[dict[str, object]]:
        """
        Cost aggregated by model: total, count, avg latency.
        """
```

### WebSocket Handler

```python
class CostWebSocketHandler:
    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}  # filter → [ws]

    async def handle(self, websocket: WebSocket) -> None:
        """
        Accept connection.
        Register on subscribe message.
        Broadcast cost updates to all matching subscribers.
        """

    async def broadcast(self, message: dict[str, object]) -> None:
        """
        Send to all connected clients whose filter matches.
        """

    async def notify_cost_update(
        self,
        task_id: str,
        amount: float,
        model: str,
        tier: str,
        running_total: float,
    ) -> None:
        """
        Called by cost_tracker after record().
        Broadcasts to all subscribers.
        """
```

## Runtime Integration

The cost tracker calls the WebSocket handler after each `record()`:

```python
class CostTracker:
    def __init__(self, event_store, ws_handler: CostWebSocketHandler | None = None):
        ...
        self._ws_handler = ws_handler

    async def record(self, ...) -> None:
        await self.event_store.append(event)
        if self._ws_handler is not None:
            await self._ws_handler.notify_cost_update(...)
```

## Error Codes (CD-001 to CD-050)

| Code  | Condition | Message |
|-------|-----------|---------|
| CD-001 | Dashboard API not initialized | "Cost dashboard service not initialized: call init() first" |
| CD-002 | Task cost not found | "No cost data for task_id {task_id}" |
| CD-003 | Session not found | "No session found for session_id {session_id}" |
| CD-004 | WebSocket connection failed | "WebSocket connection closed unexpectedly" |
| CD-005 | WebSocket send buffer full | "WebSocket send buffer exceeded {max} messages; dropping oldest" |
| CD-006 | Invalid filter expression | "Invalid WebSocket filter: {filter}. Use 'all', 'tier:N', or 'model:M'" |
| CD-007 | Query too broad | "Query matches {count} rows; set tighter filter or pagination" |
| CD-008 | Query timeout | "Cost query exceeded timeout {timeout}s" |
| CD-009–CD-050 | Reserved | Reserved for sub-features (export, alerts, budgets) |

## Test Scenarios (Phase 2)

```
Given CostTracker has recorded 10 cost events
When GET /api/v1/cost/summary returns
Then total_cost == sum of all 10 amounts
And per_tier has 1 entry for each unique tier

Given a WebSocket client subscribed to "all"
When a new task completes with cost $0.02
Then client receives { type: "cost_update", cost: 0.02 }

Given GET /api/v1/cost/tasks?limit=5&offset=0
When response is received
Then body has at most 5 entries
And entries are ordered by timestamp DESC
```
