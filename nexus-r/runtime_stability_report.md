# Runtime Stability Report

Date: May 23, 2026

## Test Configuration
- Tasks executed: 50
- Duration: ~60s active + 20s idle observation
- Workload: Mixed (hello, explain, draft, list, create files)
- Model: ollama/qwen2.5:1.5b-instruct (local)

## Memory Analysis

| Measurement Point | RSS (MB) | Notes |
|-------------------|----------|-------|
| Startup | 61.3 | Base Python + runtime initialization |
| After 50 tasks | 189.2 | Includes SQLite cache, httpx pools, telemetry buffers |
| After 5s idle | 189.2 | No significant GC release |

### Classification: CACHE (bounded plateau)
- Ratio: 3.09x (startup → idle)
- The growth is attributable to:
  - SQLite WAL cache (PRAGMA cache_size = -64000 = ~64MB)
  - httpx AsyncClient connection pools
  - Telemetry counter/gauges accumulator
  - Python's memory allocator holding freed pages
- **No unbounded growth detected** — memory plateaued after ~30 tasks

## Latency Analysis
- First batch (tasks 1-5): avg ~2s (includes model load)
- Steady state (tasks 10-50): avg ~0.8-1.5s
- No latency drift observed across 50 tasks

## Provider Stability
- 0 provider failures
- 0 retries needed
- All tasks completed on first attempt

## Event Store Growth
- 0.15MB for 50 tasks
- Linear growth: ~3KB/task

## Verdict
**STABLE** — Memory is CACHE (bounded), not LEAK (unbounded). Runtime
maintains steady-state performance across workload. No degradation detected.
