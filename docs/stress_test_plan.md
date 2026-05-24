# Stress Test Plan — Phase B

## Overview

Phase B focuses on system stability under load. All stress tests are in `tests/stress/`.

## Test 1: Concurrency Runtime (`test_concurrency_runtime.py`)

**Goal:** Verify the system handles 50+ concurrent task submissions without deadlock, race condition, or resource leak.

### Scenarios
- 50 identical tasks submitted concurrently via `asyncio.gather`
- 50 unique tasks (different inputs, paths, tools)
- Mixed read/write (history queries while tasks execute)
- Rapid submit pattern (100 tasks in 2 seconds)

### Acceptance Criteria
- All 50 tasks succeed
- No `asyncio.LimitOverrunError` or queue overflow
- EventStore WAL handles concurrent `append` calls
- Event causal chain is consistent (no parent_id pointing to missing event)
- Telemetry gauges (`active_tasks`) return to zero after completion

### Infrastructure Needed
- EventStore with large `cache_size_mb` (200+)
- `asyncio.Semaphore(50)` to control concurrency
- Timeout per task: 30s

## Test 2: Memory Pressure (`test_memory_pressure.py`)

**Goal:** Verify no memory leaks over a 30-minute sustained execution.

### Scenarios
- Run 1 task/second for 30 minutes (1800 tasks)
- Track RSS before/after with `os.getrusage` or `psutil`
- Interleave: 50% file operations, 25% LLM queries, 25% sandbox commands

### Acceptance Criteria
- Memory growth < 5% from start to end
- EventStore cache eviction maintains bounded memory
- No `gc.garbage` accumulation
- Telemetry snapshot size is stable

### Infrastructure Needed
- `psutil` for memory tracking (optional — fallback to `os.popen('tasklist')`)
- Configurable task generator
- 30-minute timer with periodic assertions

## Test 3: ETD Saturation (`test_etd_saturation.py`)

**Goal:** Verify ETD performance under 10,000+ cached entries.

### Scenarios
- Ingest 10,000 unique traces
- Query with 10,000 random intents
- Mixed: 50% matching, 50% non-matching
- Run invalidator after saturation

### Acceptance Criteria
- Ingestion: < 5ms per entry
- Query (match): < 50ms per lookup
- Query (no match): < 50ms per lookup
- Invalidator processes 10,000 entries in < 1s
- No false positives from similarity search

### Infrastructure Needed
- Pre-generated trace pool (10K variations)
- ETD pipeline with mocked sandbox
- Timer for each operation

## Run Order

1. `test_concurrency_runtime` — quick (few seconds)
2. `test_etd_saturation` — moderate (1-2 minutes)
3. `test_memory_pressure` — long (30+ minutes)

## Pass/Fail Criteria

| Test | Critical Fail | Warning |
|------|--------------|---------|
| Concurrency | Any task fails or deadlocks | >10% tasks complete in >5s |
| Memory | Growth > 10% | Growth > 5% |
| ETD Saturation | Any query > 100ms | Average query > 50ms |
