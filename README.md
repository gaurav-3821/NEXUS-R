<p align="center">
  <img src="docs/assets/nexus-r-banner.png" alt="NEXUS-R Banner" width="800">
</p>

<h1 align="center">NEXUS-R</h1>

<p align="center">
  <strong>Local-first agent runtime for executing bounded workspace tasks</strong><br>
  with auditable routing, permission checks, persistent event storage,<br>
  and a web-based operator interface.
</p>

<p align="center">
  <a href="https://github.com/gaurav-3821/NEXUS-R/actions/workflows/ci.yml">
    <img src="https://github.com/gaurav-3821/NEXUS-R/actions/workflows/ci.yml/badge.svg" alt="CI">
  </a>
  <a href="https://codecov.io/gh/gaurav-3821/NEXUS-R">
    <img src="https://codecov.io/gh/gaurav-3821/NEXUS-R/branch/main/graph/badge.svg" alt="Coverage">
  </a>
  <a href="https://github.com/gaurav-3821/NEXUS-R/releases">
    <img src="https://img.shields.io/github/v/release/gaurav-3821/NEXUS-R" alt="Release">
  </a>
  <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python">
  <img src="https://img.shields.io/badge/node-22%2B-green" alt="Node">
  <a href="LICENSE">
    <img src="https://img.shields.io/github/license/gaurav-3821/NEXUS-R" alt="License">
  </a>
</p>

---

## Overview

NEXUS-R is a modular agent runtime that bridges local AI models and cloud providers through an intelligent routing layer. It provides a secure, auditable execution environment for AI-assisted workspace tasks with full operator visibility.

<p align="center">
  <img src="docs/assets/nexus-r-dashboard-preview.png" alt="Dashboard Preview" width="700">
</p>

### Key Features

| Feature | Description |
|---------|-------------|
| **Multi-Provider Routing** | Route tasks across 10+ providers (Ollama, OpenAI, Anthropic, OpenRouter, Groq, and more) |
| **Permission Tiers** | T1-T5 escalation with deny-first destructive operations |
| **Persistent Memory** | Vector-backed conversation memory with ChromaDB |
| **Web Dashboard** | React 19 + TypeScript UI with real-time telemetry |
| **Audit Trail** | Append-only event log for every routing decision |
| **BYOK Support** | Bring Your Own Key — use your existing API credentials |

---

## Quick Start

### Prerequisites

- **Python** 3.11+ (3.12 recommended)
- **Node.js** 22+ (for frontend development)
- **Git**

### Option A: Docker (Recommended)

```bash
git clone https://github.com/gaurav-3821/NEXUS-R.git
cd NEXUS-R
make docker-up
# Open http://localhost:3000
```

### Option B: Manual Setup

```bash
git clone https://github.com/gaurav-3821/NEXUS-R.git
cd NEXUS-R

# Backend
make backend-install
make run-backend

# Frontend (new terminal)
make frontend-install
make run-frontend

# Open http://localhost:5173
```

### First Run

<p align="center">
  <img src="docs/assets/quickstart-wizard.gif" alt="First Run Wizard" width="600">
</p>

1. Open the dashboard at `http://localhost:3000`
2. Complete the setup wizard (configure your first model provider)
3. Start chatting or run workspace tasks via the CLI:

```bash
cd nexus-r
nexus run "list Python files in the workspace"
```

---

## Architecture

<p align="center">
  <img src="docs/assets/architecture-diagram.png" alt="Architecture Diagram" width="800">
</p>

### System Flow

```
User Input (CLI or Web UI)
    |
    v
Input Gateway  -->  Cognition Router  -->  Trust Layer
                                              |
                    ┌─────────────────────────┼─────────────────────────┐
                    v                         v                         v
               Local Model              Cloud Provider           Denied / Audit
               (Ollama)                (BYOK Keys)               Logged
                    |                         |
                    v                         v
              Execution Sandbox          State Core
                    |                         |
                    +-----------> Workflow Engine <---------+
                                              |
                                              v
                                       Web Dashboard
```

### Module Structure

```
nexus-r/
 foundation/nexus_r/     Shared runtime primitives (config, events, errors, telemetry)
 modules/
   cli/                  Typer entrypoints (run, history, config, dashboard)
   cognition_router/     Intelligent routing across local and cloud models
   execution_sandbox/    Workspace-scoped actions with permission enforcement
   input_gateway/        Task intent parsing and parameter extraction
   orchestrator/         End-to-end task pipeline composition
   session_manager/      Crash-safe sessions and checkpoint resume
   state_core/           Event persistence and working state
   trust_layer/          Permission enforcement, cost tracking, secrets
   web_ui/               FastAPI backend + React frontend
   workflow_engine/      Causal trace recording and workflow reuse
 frontend/               React 19 + TypeScript + Vite source code
 specs/                  Module specifications and acceptance criteria
 tests/                  Unit, integration, security, stress, and failure tests
```

---

## Development

### Setup

```bash
make setup          # Full environment setup
make install        # Install all dependencies
```

### Daily Commands

```bash
make run            # Start backend + frontend
make test           # Run all tests
make lint           # Lint all code
make format         # Format all code
make typecheck      # Type-check all code
make security       # Run security scans
make coverage       # Generate coverage report
make clean          # Clean generated files
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed contribution guidelines.

---

## Screenshots

### Chat Interface
<p align="center">
  <img src="docs/assets/screenshot-chat.png" alt="Chat Interface" width="700">
</p>

### Model Management
<p align="center">
  <img src="docs/assets/screenshot-models.png" alt="Model Management" width="700">
</p>

### Settings & Appearance
<p align="center">
  <img src="docs/assets/screenshot-settings.png" alt="Settings" width="700">
</p>

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Runtime** | Python 3.11+, FastAPI, Uvicorn |
| **CLI** | Typer |
| **Frontend** | React 19, TypeScript, Vite 8, Tailwind CSS v4 |
| **State** | Zustand |
| **Database** | SQLite (aiosqlite), ChromaDB (vectors) |
| **AI Routing** | LiteLLM, sentence-transformers |
| **Testing** | pytest, Vitest, Playwright |
| **DevOps** | Docker, GitHub Actions, Ruff, MyPy |

---

## Documentation

- [Architecture Overview](ARCHITECTURE.md)
- [Contributing Guide](CONTRIBUTING.md)
- [AI Collaboration Governance](AGENTS.md)
- [API Documentation](http://localhost:8000/docs) (auto-generated, start backend first)
- [Module Specifications](nexus-r/specs/)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [FAQ](docs/FAQ.md)
- [Changelog](CHANGELOG.md)
- [Roadmap](ROADMAP.md)

---

## Repository Activity

![Activity Graph](https://github-readme-activity-graph.vercel.app/graph?username=gaurav-3821&repo=NEXUS-R&theme=github-compact)

---

## License

[MIT](LICENSE) &copy; 2026 Gaurav Tayde

---

<p align="center">
  <sub>Built with care. Contributions welcome.</sub>
</p>
