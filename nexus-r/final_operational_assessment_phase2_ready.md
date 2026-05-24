# Final Operational Assessment — Phase 2 Ready

Date: May 24, 2026

## A. What Is Stable

The following systems are **operationally proven** with validated test coverage and production-like benchmarks:

- **ETD 7-stage pipeline** (Distiller, Generalizer, Parameterizer, Indexer, Retriever, Invalidator, Applicator). End-to-end validated: first-run creates cache entry, second-run retrieves and applies with 100% cost reduction and 48.5% latency reduction. 113 tests pass.
- **Local model runtime** (`ollama/qwen2.5:1.5b-instruct`). Real inference, streaming, cancellation, concurrency at 20/50/100 tasks with zero failures.
- **BYOK fallback** (`groq/llama-3.3-70b-versatile` via litellm). Non-zero cost accounting, provider error specificity, timeout-triggered fallback chain.
- **EventStore with SQLite WAL**. Batched append at 0.023 ms/event, causal chain lookup at 3.95 ms for depth 100.
- **Session recovery**. Checkpoint/resume across orchestrator restarts, sequence tracking, stale-pointer repair.
- **Structured telemetry**. JSON-line output with counters, gauges, provider activity, and failure classification.

## B. What Is Prototype (Specified, Not Implemented)

These components have written specifications but **no production implementation**:

- **4-tier CAR (Cognition Action Router)** — `specs/02_cognition_router.spec.md` describes a 4-tier fallback chain architecture. The current router implements a single `route()` call with a 2-tier local/byok model selection — not the full multi-tier routing with cascading fallback across heterogeneous providers.
- **Cost dashboard** — `specs/07_cost_dashboard.spec.md` defines a real-time cost visualization layer with provider-level breakouts and trend analysis. Only the `CostTracker` and `get_cost_summary()` API exist. No dashboard UI or persisted cost warehouse is implemented.
- **ETD store persistence** — The ETD store is currently in-memory only. A SQLite-backed persistence layer is specified but not implemented.

## C. What Breaks First

Under production load, these are the expected failure points:

- **Sandbox overhead on ETD cached execution (3.7s cached vs 0.5s theoretical).** The cached path still invokes the execution sandbox for each step. The sandbox's file-listing, terminal-command dispatch, and event logging add ~3.7s per cached task. Achieving <0.5s requires sandbox bypass for pure-ETD replay.
- **Cold CLI latency (~8s).** The first `nexus run` command loads the model stack (litellm, provider chain, warm-up). Acceptable for development, unacceptable for interactive CLI use.
- **Concurrency degradation under local model inference.** The single-threaded Ollama bottleneck causes linear latency growth under concurrent task load (p95 61s at 100 tasks).

## D. Highest Risk (Before Production)

These risks require mitigation before unattended or multi-user operation:

- **Cross-store atomicity.** EventStore (SQLite), WorkingStateStore (in-memory dict), SessionManager (separate SQLite), and ETDStore (in-memory dict) have no coordinated commit boundary. A crash between stores produces inconsistent state.
- **Windows path edge cases.** The sandbox's `_list_files_sync` and `_list_files_sync_windows` use `Path.rglob()` which handles forward/backward slashes inconsistently across Python versions. `recursive=True` with mixed slash conventions can miss files on Windows.
- **No circuit breaker for failing providers.** A down provider is retried on every request, adding 1-2s of timeout overhead each time.
- **Single-file SQLite with no HA strategy.** Loss of `events.sqlite3` or `session_runtime.sqlite3` means complete state loss.
- **BYOK credential lifecycle.** API key is read once at startup; mid-session expiry causes silent failures until the next `refresh()` cycle.

## E. Needs Redesign Before Phase 3

These architectural decisions should be revisited before Phase 3, but do not block Phase 2:

- **Sandbox execution speed.** The sandbox wraps every operation (even metadata lookups like `list_files`) in full event recording, task construction, and handler dispatch. A lightweight inline execution path for ETD replay would eliminate the overhead without redesigning the sandbox itself.
- **Trace data model for terminal commands.** The current `ToolStep.action` stores only the action type (e.g., `"run_terminal"`), not the actual command. Terminal ETD replay cannot work without embedding the command string or parameters in the trace. This requires a `ToolStep.command` field or equivalent.
- **ETD store architecture.** The in-memory dict-backed store is sufficient for single-user single-session use. For multi-session or persistent caching, a SQLite-backed store with TTL-based compaction is needed. The store interface (`add/get/update/remove/list_active/list_all`) is stable and can be backed by any key-value store.
