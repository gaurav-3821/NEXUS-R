# NEXUS-R Package Overview

This directory contains the main product code, package metadata, specs, tests,
automation scripts, and frontend source for NEXUS-R.

## Directory Map

- `pyproject.toml`: package metadata, dependencies, and CLI entrypoint
- `foundation/nexus_r/`: shared runtime code used across modules
- `modules/`: subsystem implementations
- `frontend/`: React + TypeScript + Vite UI source
- `specs/`: architecture and subsystem specifications
- `tests/`: unit, integration, security, stress, and failure coverage
- `scripts/`: validation, recovery, benchmark, and stress helpers
- `docs/`: package-local reports and validation summaries

## Main Runtime Path

The runtime is composed through `modules/orchestrator/src/orchestrator.py` and
exposed through the CLI in `modules/cli/src/main.py`.

Primary user-facing entrypoints:

- `nexus run "<task>"`
- `nexus history`
- `nexus cost`
- `nexus config`
- `nexus dashboard start`

## Modules

- `input_gateway`: task parsing and normalization
- `cognition_router`: model selection and routing decisions
- `execution_sandbox`: workspace-scoped action execution
- `state_core`: event store, working state, identity, and projections
- `workflow_engine`: trace capture, ETD pipeline, and workflow reuse storage
- `trust_layer`: permissions, cost, secrets, and risk controls
- `session_manager`: durable runtime session checkpoints
- `orchestrator`: end-to-end runtime composition
- `web_ui`: backend application for the dashboard
- `cli`: command-line interface

## Frontend And Dashboard

The frontend source lives in `frontend/`. The backend serves built files from
`modules/web_ui/src/static/`.

That means dashboard changes may involve two layers:

1. source edits in `frontend/`
2. generated build output synced into `modules/web_ui/src/static/`

## Development Notes

- Package metadata currently requires Python `>=3.11`.
- Some historical documents in the repository still refer to earlier phase
  labels or implementation boundaries.
- Tests are organized by unit, integration, security, stress, and failure
  scenarios instead of by a single monolithic suite.
