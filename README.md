# NEXUS-R

NEXUS-R is a local-first agent runtime for executing bounded workspace tasks
with auditable routing, permission checks, persistent event storage, and a
web-based operator interface.

The repository is active and not feature-complete. It contains a working
runtime foundation, an evolving routing and workflow layer, a FastAPI-served
dashboard, and supporting validation artifacts from earlier implementation
phases.

## What The Repo Contains

- `nexus-r/`: the product codebase, package metadata, specs, tests, and scripts
- `nexus-r/foundation/nexus_r/`: shared runtime primitives such as config,
  events, errors, telemetry, and backend management
- `nexus-r/modules/`: modular subsystems including routing, sandboxing, state,
  workflow, trust, sessions, orchestration, CLI, and web UI
- `nexus-r/frontend/`: React 19 + TypeScript + Vite source for the current UI
- `nexus-r/modules/web_ui/src/static/`: built frontend assets served by the
  backend
- `docs/`: reports, planning material, exported PDFs, and supporting reference
  documents
- `.nexus-intel/`: task, governance, and audit scaffolding for AI-assisted work

## Current Product Shape

The codebase is organized around a small set of runtime responsibilities:

- Input parsing for bounded natural-language tasks
- Model routing across local and BYOK options
- Workspace-confined execution with permission enforcement
- Append-only event persistence and resumable working state
- Trace capture for workflow reuse and future ETD expansion
- Web UI and dashboard endpoints for runtime visibility

The implementation and documents are still catching up to each other in a few
areas. When in doubt, treat source code, tests, and package metadata as more
reliable than older summaries.

## Stack

- Python package: `nexus-r`
- Minimum Python version in package metadata: `3.11`
- Backend runtime: FastAPI + Uvicorn
- CLI: Typer
- Frontend source: React, TypeScript, Vite, Zustand, Tailwind
- Testing: pytest

## Quick Start

```bash
git clone https://github.com/gaurav-3821/NEXUS-R.git
cd NEXUS-R/nexus-r
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

Run the CLI:

```bash
nexus run "list python files in the workspace"
```

Start the dashboard:

```bash
nexus dashboard start
```

If the dashboard dependencies are missing, install them in the active
environment:

```bash
pip install fastapi uvicorn
```

## Where To Read Next

- [Architecture](/C:/Users/Gaurav/Documents/NEXUS-R/ARCHITECTURE.md)
- [Contributing](/C:/Users/Gaurav/Documents/NEXUS-R/CONTRIBUTING.md)
- [Product package overview](/C:/Users/Gaurav/Documents/NEXUS-R/nexus-r/README.md)
- [Docs index](/C:/Users/Gaurav/Documents/NEXUS-R/docs/INDEX.md)
- [AI collaboration governance](/C:/Users/Gaurav/Documents/NEXUS-R/.nexus-intel/README.md)

## Repository Notes

- Built frontend assets under `nexus-r/modules/web_ui/src/static/` are present
  in the repo today because the backend serves them directly.
- The worktree may contain active product changes that are not yet reflected in
  the top-level documentation.
- Historical reports are retained for traceability; see the docs index instead
  of treating every report as current status.
