# Phase 1 Architecture Review

## Executive Summary

Phase 1 is functional as a local CLI demo, but it is not yet a credible agent runtime architecture. The biggest issue is structural: the code does not execute any real model calls. The "local vs BYOK" router is currently a label-and-cost selector, not an execution boundary. That means the system is closer to a deterministic command interpreter with audit logging than to the agent runtime described in the PDFs.

## Highest-Risk Findings

### 1. CAR is not real yet

- `modules/orchestrator/src/orchestrator.py:100-134` routes tasks and logs the selected model, but nothing ever invokes a model.
- `foundation/nexus_r/model_registry.py:33-50` only exposes static availability and estimated cost metadata.
- Result: the most important product claim, progressive local vs BYOK cognition routing, is not implemented.

### 2. The orchestrator is tightly coupled to concrete modules

- `modules/orchestrator/src/orchestrator.py:18-28` directly constructs every dependency.
- There are no ports/interfaces for parser, router, sandbox, state, or trust layers.
- Result: the orchestrator is acting as a god-object and Phase 2 changes will keep increasing edit blast radius.

### 3. Event persistence is append-heavy but connection-inefficient

- `foundation/nexus_r/events.py:144-169` opens a fresh SQLite connection per append.
- Benchmarks show `250` writes took `10650.43 ms`, which is poor for the event log that everything depends on.
- Result: write amplification and connection churn will become a bottleneck before Phase 2 ETD volume arrives.

### 4. Failure recovery is now safer, but still best-effort

- `modules/orchestrator/src/orchestrator.py:135-151` catches runtime exceptions and attempts to log `task_error`.
- `modules/orchestrator/src/orchestrator.py:205-214` now degrades when `task_completed` cannot be persisted.
- Result: caller crashes are reduced, but audit completeness is still not guaranteed under database-lock scenarios.

## Coupling Review

### Orchestrator <-> Event Store

- Very high coupling. Every lifecycle step is manually appended in the orchestrator.
- Good for audit explicitness, bad for change isolation.
- Future risk: Phase 2/3 features will force orchestrator rewrites for every new event type.

### Orchestrator <-> Sandbox

- High coupling. The orchestrator assumes a single-step sandbox execution model.
- There is no step planner, no multi-step executor abstraction, and no iterative tool loop.
- Future risk: browser automation, replay, and ETD composition will not fit cleanly.

### CLI <-> Orchestrator

- Moderate coupling.
- CLI stays thin, which is good.
- Packaging remains slightly awkward because source execution relies on import-path shims.

### Router <-> Trust Layer

- Weak coupling in a bad way.
- Router does not consume secret storage, provider health, runtime latency, or permission cost caps beyond static estimates.
- Future risk: policy and routing will diverge into inconsistent sources of truth.

## Overengineered Now

- Dual package exposure via both `foundation/nexus_r` and `nexus_r` shim package.
- `modules/state_core/src/event_store.py` exists only as a re-export layer.
- Interface YAML files are present, but there is no code using them yet.

## Underengineered Now

- Real model execution path
- Provider error handling
- Provider timeout handling
- Persistent task/session lifecycle
- Multi-step workflow abstraction
- Identity/secret boundary hardening
- Structured logging beyond SQLite events

## Scalability Risks

1. SQLite write path will become a bottleneck under ETD-heavy workloads.
2. `WorkingStateStore` is process-local only and unsuitable for multi-process or daemonized execution.
3. The parser is heuristic-only and will plateau quickly on real user task variety.
4. Cost tracking is synthetic today and will drift from reality when real providers are added.
5. Because model execution is absent, Phase 2 could accidentally build on a false baseline.

## Honest Verdict

Phase 1 is acceptable as a hardening target for a prototype, not as a trustworthy foundation for Phase 2. The architecture needs at least one more pass on provider execution boundaries, persistence strategy, and orchestrator decomposition before the system claims start matching the runtime behavior.
