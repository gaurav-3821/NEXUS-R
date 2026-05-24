# Cost Dashboard Deployment Guide

## Overview

The Cost Dashboard provides real-time cost visualization, audit log search, and ETD cache statistics through a FastAPI backend with WebSocket push.

## Architecture

```text
Client Browser <-> FastAPI (port 8400) <-> EventStore (SQLite)
                    |
                    +-> WebSocket (ws://host:8400/ws/v1/cost/live)
                    |
                    +-> Runtime CostTracker (push)
```

## Prerequisites

- Python 3.11+
- FastAPI 0.100+ (`pip install fastapi uvicorn`)
- NEXUS-R runtime with EventStore and optionally ETDStore

## Installation

```bash
# From the nexus-r directory
pip install fastapi uvicorn

# Or with all dev dependencies
pip install -e ".[dev]"
```

## Configuration

Set the dashboard authentication token:

```bash
$env:NEXUS_DASHBOARD_TOKEN="your-secret-token-here"
```

Do not rely on the generated in-memory token for shared or production-like environments. Set `NEXUS_DASHBOARD_TOKEN` explicitly so access is reproducible and auditable.

## Running

### Standalone (for development)

```bash
python -m uvicorn modules.web_ui.src.app:create_app --factory --host 0.0.0.0 --port 8400 --reload
```

### Via Python script

```python
import asyncio
from foundation.nexus_r.events import EventStore
from modules.web_ui.src.app import create_app
import uvicorn

async def main():
    store = EventStore("/path/to/events.db")
    app = create_app(store)
    config = uvicorn.Config(app, host="0.0.0.0", port=8400, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

asyncio.run(main())
```

## Usage

1. Open `http://localhost:8400` in a browser.
2. Add `?token=your-token` to the URL.
3. The Overview tab shows total spend, cost by tier, cost by model, and recent tasks.
4. The Tasks tab provides paginated task cost listing with tier/model filters.
5. The Audit Log tab provides searchable, filterable cost events by `task_id`, model, date range, and cost range.
6. The ETD Cache tab shows cached workflows with hit rate, success rate, average cost, and average latency.
7. The Models tab shows per-model cost breakdown.

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/cost/summary` | GET | Total spend, per-tier, per-model breakdown |
| `/api/v1/cost/tasks` | GET | Paginated task list with limit, offset, tier, model, date range, and cost range |
| `/api/v1/cost/task/{task_id}` | GET | Single task with per-step breakdown |
| `/api/v1/cost/session/{session_id}` | GET | Session aggregate for tasks matching the `session_id` prefix |
| `/api/v1/cost/tiers` | GET | Cost aggregated by permission tier |
| `/api/v1/cost/models` | GET | Cost aggregated by model |
| `/api/v1/etd` | GET | ETD cache entries with stats |
| `/api/v1/audit/log` | GET | Searchable, paginated cost audit log |
| `/api/v1/dashboard` | GET | Dashboard HTML page |
| `/ws/v1/cost/live` | WS | Real-time cost updates |

## Authentication

All API endpoints except `/`, `/static/*`, and `/docs` require a token:

- Query parameter: `?token=your-token`
- The token is read from `NEXUS_DASHBOARD_TOKEN`
- If no token is configured, the app uses an ephemeral in-memory token for the current process only

## Rate Limiting

- 100 requests per minute per endpoint
- WebSocket connections are exempt
- Exceeding the limit returns HTTP 429 with `Retry-After`

## WebSocket Protocol

### Server -> Client messages

```json
{"type": "cost_update", "task_id": "...", "cost": 0.02, "model": "...", "tier": "T2", "running_total": 0.15}
{"type": "task_started", "task_id": "...", "estimated_cost": 0.01}
{"type": "task_completed", "task_id": "...", "final_cost": 0.02, "latency_ms": 150.0}
{"type": "session_reset", "total_cost": 0.0}
{"type": "ping"}
```

### Client -> Server messages

```json
{"type": "subscribe", "filter": "all"}
{"type": "subscribe", "filter": "tier:T1"}
{"type": "subscribe", "filter": "model:groq/llama3"}
{"type": "unsubscribe"}
```

## Error Codes

| Code | Condition |
|---|---|
| CD-001 | Dashboard API not initialized |
| CD-002 | Task cost not found |
| CD-003 | Session not found |
| CD-004 | WebSocket connection failed |
| CD-005 | WebSocket send buffer full |
| CD-006 | Invalid WebSocket filter |
| CD-007 | Query too broad (>5000 rows) |
| CD-008 | Query timeout |

## Running Tests

```bash
pytest tests/unit/test_cost_dashboard.py -v
pytest tests/integration/test_dashboard_api.py -v
pytest tests/security/test_dashboard_security.py -v

# Coverage
pytest --cov=modules.web_ui --cov-report=term-missing tests/
```

## Limitations

- Cost data is event-sourced from EventStore, so historical coverage depends on retention policy.
- ETD cache is in-memory only; stats reset on restart.
- Rate limiting is per-process, not distributed.
- No TLS is enabled by default; use a reverse proxy such as nginx or caddy for production.
