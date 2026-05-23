# Phase 1.5 Runtime Truthfulness Report

Date: May 23, 2026

## A. REAL Systems

- Local model execution is real.
  - Model: `ollama/qwen2.5:1.5b-instruct`
  - Verified via `nexus run "hello"` returning a real model response and non-zero cost.
- Local streaming is real.
  - Verified with `22` streamed chunks from the local Ollama model.
- Real local concurrency is real.
  - Verified at `20`, `50`, and `100` concurrent orchestration tasks with zero task failures.
- SQLite event persistence is real.
  - Verified with real writes, reads, causal chains, and cost-history accumulation.
- Structured runtime telemetry is real.
  - The runtime now emits JSON-line telemetry and maintains counters/gauges for provider activity, failures, and event-store writes.

## B. PARTIAL Systems

- EventStore performance is partially solved.
  - Batch append is strong.
  - Strict synchronous single-append latency still misses the `<1 ms` target.
- Failure handling is partially real.
  - Database locks, sandbox violations, injected provider timeouts, and partial event-write failures were observed and handled.
  - Some provider-failure surfaces remain too generic.
- Sustained event logging during inference is partially proven.
  - The task remained live mid-flight and provider-result persistence was confirmed after completion.
  - Mid-flight visibility of the exact provider-invocation event is still timing-sensitive.
- Cost accounting is partially real.
  - Non-zero costs are recorded for real local execution.
  - The numbers are still policy/config-driven, not true infrastructure metering.

## C. MOCK / FALLBACK Systems

- BYOK fallback remains mock-only on this machine.
  - No real BYOK API key was available.
  - The observed local-failure recovery path fell back to `mock-byok`.
- Some failure-mode simulations use fake local servers or injected exceptions.
  - These are useful for exercising recovery logic.
  - They are not the same as a real remote-provider outage.

## D. UNVERIFIED Assumptions

- Real BYOK execution and real local-to-BYOK escalation are unverified.
- Ollama shutdown during an in-flight orchestrator task is unverified in the committed validation artifacts.
- Provider-malformed-wire-protocol handling against a true provider implementation is unverified.
- Production-grade secret lifecycle and operator-facing incident workflows are unverified.

## Bottom Line

Phase 1.5 is no longer a simulated framework. It is a real local-runtime foundation with real model execution, real persistence, and real telemetry.

It is not yet fully proven as a production-trustworthy 2-tier runtime because the BYOK side is still unvalidated and the synchronous EventStore hot path still misses its original latency target.
