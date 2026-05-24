# NEXUS-R

NEXUS-R is a personal agent runtime focused on auditable execution, conservative permissions, and measurable repeat-task acceleration through Execution Trace Distillation (ETD).

## Current Status

- Phase 2 validation baseline frozen at `77423c0` (`phase2-validation-freeze`)
- Six active subsystems: Input Gateway, Cognition Router, Execution Sandbox, State Core, Workflow Engine, Trust Layer
- Cost Dashboard included for API- and WebSocket-based runtime telemetry
- Validation artifacts and reproducibility reports live under [`docs/`](C:\Users\Gaurav\Documents\NEXUS-R\nexus-r\docs)

## Core Capabilities

- Natural-language task intake with explicit intent classification
- Conservative routing across local, BYOK, and managed model tiers
- Workspace-scoped terminal and filesystem execution
- SQLite-backed append-only event sourcing for auditability
- ETD caching for repeat-task latency and cost reduction
- Real-time cost and audit visibility through the FastAPI dashboard

## Deferred By Design

- Browser automation
- Authenticated browser/session management implementation
- Distributed rate limiting and multi-node coordination
- Container-level sandbox isolation

## Cost Dashboard

The dashboard exposes cost summaries, task history, audit log search, ETD cache statistics, and real-time updates over WebSocket.

### Quick Start

```bash
pip install fastapi uvicorn
$env:NEXUS_DASHBOARD_TOKEN="your-token"
python -m uvicorn modules.web_ui.src.app:create_app --factory --host 0.0.0.0 --port 8400
```

Open `http://localhost:8400?token=your-token`.

### API Surface

| Endpoint | Description |
|---|---|
| `GET /api/v1/cost/summary` | Total spend, per-tier, per-model breakdown |
| `GET /api/v1/cost/tasks` | Paginated task list with filters |
| `GET /api/v1/cost/task/{id}` | Single task with per-step cost |
| `GET /api/v1/cost/session/{id}` | Session aggregate |
| `GET /api/v1/cost/tiers` | Cost by permission tier |
| `GET /api/v1/cost/models` | Cost by model |
| `GET /api/v1/etd` | ETD cache statistics |
| `GET /api/v1/audit/log` | Searchable, paginated audit log |
| `WS /ws/v1/cost/live` | Real-time cost updates |

### Runtime Shape

```text
Browser <-> FastAPI (port 8400) <-> EventStore (SQLite)
             |
             +-> WebSocket (ws://host:8400/ws/v1/cost/live)
             |
             +-> Runtime CostTracker (push)
```

## Validation Highlights

- Phase 2 validation summary: [`docs/phase2_validation_summary.md`](C:\Users\Gaurav\Documents\NEXUS-R\nexus-r\docs\phase2_validation_summary.md)
- Cost dashboard deployment guide: [`docs/cost_dashboard_deployment.md`](C:\Users\Gaurav\Documents\NEXUS-R\nexus-r\docs\cost_dashboard_deployment.md)
- EventStore scaling report: [`docs/eventstore_scaling_report.md`](C:\Users\Gaurav\Documents\NEXUS-R\nexus-r\docs\eventstore_scaling_report.md)
- Provider failure report: [`docs/provider_failure_report.md`](C:\Users\Gaurav\Documents\NEXUS-R\nexus-r\docs\provider_failure_report.md)
- Recovery guide for local test environments: [`docs/test_environment_recovery.md`](C:\Users\Gaurav\Documents\NEXUS-R\nexus-r\docs\test_environment_recovery.md)
