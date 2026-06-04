# NEXUS-R Architecture

This document describes the current repository-level architecture: what modules
exist, how they fit together, and where the main execution boundaries are.

## Runtime Shape

NEXUS-R is structured as a modular Python runtime with a separate frontend
source tree and a backend-served static dashboard build.

```text
User Input
  -> CLI or Web UI
  -> Input Gateway
  -> Cognition Router
  -> Trust checks
  -> Execution Sandbox or model completion
  -> State Core + Session Manager
  -> Workflow trace recording
  -> Result, history, and cost views
```

## Main Components

### Foundation

`nexus-r/foundation/nexus_r/`

Shared runtime primitives:

- configuration loading
- event and result types
- telemetry and logging
- backend startup helpers
- shared error definitions
- model registry utilities

### Modules

`nexus-r/modules/`

- `input_gateway`: parses bounded task intent and extracts parameters
- `cognition_router`: chooses local or BYOK execution paths and records routing
  rationale
- `execution_sandbox`: performs workspace-scoped actions with confinement and
  deny-first behavior for destructive operations
- `state_core`: persists events, tracks working state, and stores derived
  identity/runtime views
- `workflow_engine`: records causal traces and provides the storage and pipeline
  surface for workflow reuse
- `trust_layer`: permission enforcement, cost tracking, secret management, and
  prompt-risk related controls
- `session_manager`: crash-safe session catalog and checkpoint resume support
- `orchestrator`: composes the runtime into an end-to-end task pipeline
- `cli`: Typer entrypoints for task execution, history, cost, config, and
  dashboard startup
- `web_ui`: FastAPI application and static asset serving for the dashboard

### Frontend

`nexus-r/frontend/`

The current frontend source is a React + TypeScript + Vite application. Its
production build is copied into `nexus-r/modules/web_ui/src/static/`, which the
backend serves.

## Execution Boundaries

### Model routing

The router is responsible for selecting an execution path based on intent,
configured models, and runtime constraints. The repo currently includes local
and BYOK-oriented routing code, along with model registry and download-related
supporting files.

### Sandbox

The sandbox is designed around workspace confinement. Filesystem and terminal
actions are scoped to the configured workspace, and destructive operations are
denied unless explicitly supported by a higher trust tier.

### Persistence

The event store is the main durable record of runtime actions. Session
checkpointing layers on top of that to support restart and recovery workflows.

### Workflow capture

Successful and failed executions generate traces that can later support ETD and
workflow reuse. The repository includes both the trace pipeline and report
artifacts from prior validation work.

## Supporting Materials

- Product specs: `nexus-r/specs/`
- Tests: `nexus-r/tests/`
- Validation and planning reports: `docs/`

Some historic documents still describe earlier phase boundaries. Use them as
context, not as the final word on what the current source tree implements.
