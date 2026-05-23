# NEXUS-R

> **A personal agent runtime that makes AI task execution progressively cheaper through verified workflow reuse.**

NEXUS-R builds the execution layer for autonomous AI agents — the runtime that makes agents cheaper to operate over time, not more expensive. We are a systems-engineering project focused on:

*   **Operational correctness** over demo polish
*   **Failure recovery** over feature count
*   **Cost transparency** over black-box magic
*   **Local-first privacy** over cloud dependency

---

## 📖 What This Is

Current AI agent architectures treat every execution as a novel problem, routing each request to the most expensive model regardless of history. This is economically unsustainable at scale.

**NEXUS-R inverts this.** Our core mechanism, Execution Trace Distillation (ETD), transforms successful agent executions into reusable, parameterized workflows with quantified reliability guarantees. 

This is *not* just caching. It is verified knowledge accumulation.

Instead of routing to the most expensive model regardless of history, NEXUS-R:
1. **Records** every execution as an immutable, causal event stream.
2. **Distills** successful traces into reusable, parameterized workflows (ETD).
3. **Verifies** workflow generalization across task variants (>90% success threshold).
4. **Routes** intelligently — local models for routine work, cloud only when necessary.
5. **Caches** proven execution plans, making repeated tasks faster and cheaper.

The result: **progressive cost reduction** through accumulated workflow knowledge, not subscription discounts.

---

## ⚡ Quick Start

### Prerequisites
*   Python 3.12+
*   [Ollama](https://ollama.com/) installed locally
*   Windows, macOS, or Linux

### Install
```bash
git clone https://github.com/gaurav-3821/NEXUS-R.git
cd NEXUS-R/nexus-r
pip install -e ".[dev]"
```

### Pull a Local Model
```bash
ollama pull qwen2.5:1.5b-instruct
```

### Run Your First Task
```bash
nexus run "list all python files in the workspace"
```

**Expected output:**
```
[Intent]  code  |  confidence: 0.94  |  T1 (read-only)
[Route]   local_7b via Ollama  |  $0.00  |  privacy=max
[Trust]   T1 auto-approved
[Exec]    ls *.py
[Verify]  exit_code=0
[Result]  main.py, parser.py, test_parser.py

[Cost]    $0.000  |  0 tokens  |  1.2s  |  Tier T1
[Audit]   evt_a1b2c3 → EventStore
```

### Check History and Cost
```bash
nexus history   # Full audit trail
nexus cost      # Cumulative cost breakdown
nexus config    # Current settings
```

---

## 🏗️ Architecture

NEXUS-R is built on five subsystems and six implementation modules, with a cross-cutting Trust and Control Layer.

```text
┌─────────────────────────────────────────────────────────────┐
│    Input Gateway   →   Cognition Router   →   Execution Sandbox │
│   (Intent Parser)        (CAR + ISE)           (MCP Tools)      │
├─────────────────────────────────────────────────────────────┤
│    State Core                  →               Workflow Engine  │
│  (Event Store + Memory)                       (ETD Pipeline)    │
├─────────────────────────────────────────────────────────────┤
│         Trust Layer (Permissions, Audit, Cost, Secrets)         │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Decisions:
*   **Event-sourced everything** — Every state change is an immutable event. Enables replay, debugging, and ETD extraction.
*   **MCP everywhere** — All tool integrations via Model Context Protocol. No custom connectors.
*   **LiteLLM for model abstraction** — Unified interface for 100+ providers. We don’t build our own router.
*   **Deny-first security** — ML risk classifier embedded in execution. Default is deny; allow is earned.
*   **Privacy as hard constraint** — Local models always preferred when privacy flag is set. Not a preference.
*   **Explicit generalization bounds** — No workflow applied without >90% proven success rate.

See `docs/ARCHITECTURE.pdf` (or `ARCHITECTURE.md`) for the full subsystem design.

---

## 📊 Current State: Phase 1.5 (COMPLETE)

| Component | Status | Evidence |
| :--- | :--- | :--- |
| **Local model execution** | ✅ Real | `qwen2.5:1.5b-instruct` validated, streaming, cancellation |
| **Event-sourced persistence** | ✅ Real | SQLite WAL, <1ms batched append, causal chaining |
| **Capability-Aware Routing (CAR)** | ✅ Real | 2-tier local/BYOK with fallback chain |
| **Execution Sandbox** | ✅ Real | Workspace-scoped filesystem, Docker/subprocess isolation |
| **Permission & Trust Layer** | ✅ Real | T1–T2 enforced, deny-first, audit logging |
| **Telemetry & Observability** | ✅ Real | Structured JSON logging, timing spans, queue metrics |
| **Concurrency & Stress** | ✅ Real | 100 concurrent tasks, zero failures |
| **BYOK Cloud Fallback** | ⚠️ Wired, unverified | Architecture ready, awaits live API key validation |

**Next Phase (Phase 2):** ETD pipeline, full 4-tier routing, and cost dashboard.

---

## 🚀 Performance

Measured on a standard development workstation (Windows 11, 16GB RAM, SSD):

| Metric | Result |
| :--- | :--- |
| Routing overhead | <50ms |
| T1 task end-to-end (local) | ~1.9s avg, ~12s max |
| EventStore batch append | 0.024ms/event (10K events in 233ms) |
| 100 concurrent tasks | 100% success, zero failures |
| Test coverage | >80% |

---

## 🤝 Getting Involved & Contributing

We welcome contributors who care about operational correctness, failure recovery, and engineering honesty. 

*   Review our [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and methodologies.
*   Check [open issues](https://github.com/gaurav-3821/NEXUS-R/issues) tagged `good-first-issue`.

### Contact
*   Security reports: `security@nexus-r.dev`
*   General: `hello@nexus-r.dev`

---

## ⚖️ License
MIT License — See `LICENSE` for details.

*“The AI agent that gets cheaper the more you use it.”*  
**This is the pitch. This is the moat. Everything else is implementation.**
