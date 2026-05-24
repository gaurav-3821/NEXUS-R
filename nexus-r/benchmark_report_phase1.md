# Phase 1.5 Benchmark Report

## Environment

- Date: May 23, 2026
- Platform: Windows local
- Python: project-local `.venv`
- Local model: `ollama/qwen2.5:1.5b-instruct`

## Measured Results

| Metric | Result |
|--------|--------|
| Orchestrator startup | `519.18 ms` |
| Real 20-task batch success rate | `100%` |
| Real 20-task batch average latency | `1917.48 ms` |
| Real 20-task batch max latency | `12140.51 ms` |
| Streaming response chunks | `22` |
| 20 concurrent orchestration tasks | `27.03 s total`, `p50 20.99 s`, `p95 26.51 s` |
| 50 concurrent orchestration tasks | `35.59 s total`, `p50 21.42 s`, `p95 33.60 s` |
| 100 concurrent orchestration tasks | `63.88 s total`, `p50 39.54 s`, `p95 61.26 s` |
| SQLite sequential append 10,000 events | `11.61 s total`, `1.161 ms/append` |
| SQLite batch append 10,000 events | `233.78 ms total`, `0.0234 ms/append` |
| Event chain lookup length 100 | `3.95 ms` |
| CLI `config` cold run | `1357.79 ms` |
| CLI `run hello` cold run | `8067.73 ms` |

## What Passed

- Real local inference is now live through Ollama.
- Streaming, cancellation, and long-context requests completed on the real local model.
- Concurrent orchestration runs stayed stable at `20`, `50`, and `100` tasks with no task failures.
- Batch event persistence is strong.

## What Failed

- The EventStore target of `<1 ms` for synchronous single-event append is still not met.
- Cold CLI latency is too high for a lightweight local tool once a real model is involved.
- Concurrency remains operational, but not fast. The runtime degrades linearly under load because the local model is the bottleneck.

## Interpretation

The system is now benchmarked against a real local model, which makes these numbers materially more honest than the earlier Phase 1 report. The local runtime is functional, but it is not yet efficient under cold-start or high-concurrency conditions.

The EventStore redesign succeeded for batched persistence, not for strict synchronous single-append latency. That matters because the current orchestrator still emits many single events in the hot path.

## ETD Cost Reduction Validation

The Experience Trace Database (ETD) 7-stage pipeline was validated end-to-end. The same task (`list all python files`) was executed 5 times through `MainOrchestrator`. First execution creates an ETD entry; subsequent executions retrieve and apply it.

| Execution | Route    | Source | Cost    | Latency  | Success |
|-----------|----------|--------|---------|----------|---------|
| 1         | model    | model  | $0.0750 | 7234 ms  | True    |
| 2         | etd      | cached | $0.0000 | 3734 ms  | True    |
| 3         | etd      | cached | $0.0000 | 3766 ms  | True    |
| 4         | etd      | cached | $0.0000 | 3828 ms  | True    |
| 5         | etd      | cached | $0.0000 | 3578 ms  | True    |

- **Cost reduction**: 100% (cached runs incur $0.000)
- **Latency reduction**: 48.5% (7234 ms → 3726 ms average)
- **ETD hit rate**: 80% (4 of 5 from cache)
- **Pipeline stages validated**: Distiller, Generalizer, Parameterizer, Indexer, Retriever, Invalidator, Applicator
- **113 unit + integration tests pass** across all 7 modules

Three bugs were discovered and fixed during validation:
1. **Embedding mismatch** — query embedded from `normalized_input`, stored entry from `intent_signature` (different strings → different hash vectors)
2. **Type-match delimiter mismatch** — underscore vs hyphen in action type comparison
3. **Applicator action mapping** — `execution_sandbox` mapped to `run_terminal` instead of forwarding the action as the action type

## Performance Conclusions

1. Real local inference works, but the first-call model load and CPU-bound generation dominate latency.
2. Batch persistence is good enough for Phase 1.5; synchronous append performance still misses the original hard target.
3. ETD caching provides 48.5% latency reduction for sandbox tasks. Model-invocation tasks would benefit more (100% vs ~48%) but are gated by applicator's sandbox-only tool support.
4. Phase 2 should not assume that current concurrency numbers leave much headroom for additional orchestration or web overhead.
