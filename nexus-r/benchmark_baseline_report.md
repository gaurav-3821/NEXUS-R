# Benchmark Baseline Report — Phase 2

**Date:** 2026-05-24  
**Commit:** 3cf25ef  
**Status:** FROZEN

## ETD Latency Reduction (Baseline)
| Metric | Value | Threshold | Status |
|---|---|---|---|
| Mean reduction | 96.77% | ≥40% | PASS |
| First-run mean latency | 1254.6 ms | — | Documented |
| Second-run mean latency | 40.5 ms | — | Documented |
| Trials completed | 10/10 | ≥10 | PASS |
| All trials improved | Yes | — | PASS |
| Paired t-test p-value | <0.000001 | <0.05 | PASS |
| First-run CV | 0.0237 | — | Low variance |
| Second-run CV | 0.1868 | — | Moderate (due to async scheduler) |

## Benchmark Reproducibility
| Metric | Value | Threshold | Status |
|---|---|---|---|
| Passes | 10 | 10 | PASS |
| All passes successful | Yes | Yes | PASS |
| Prompts with CV<10% | 4/4 | 4/4 | PASS |
| Latency CV range | 0.0412–0.0859 | ≤0.10 | PASS |
| Cost CV | 0.0000 | ≤0.10 | PASS |
| Load impact (under 500 pre-populated events) | 4/4 success | — | PASS |
| Session persistence | Confirmed | — | PASS |

### Per-Prompt Latency Statistics
| Prompt | Mean (ms) | Std (ms) | CV |
|---|---|---|---|
| hello world | 3796 | 326 | 0.0859 |
| explain what a database is in one sentence | 3867 | 174 | 0.0450 |
| draft a short commit message | 3906 | 161 | 0.0412 |
| list all python files | 2611 | 128 | 0.0491 |

## Concurrency Stress
| Scale | Tasks | Success Rate | Status |
|---|---|---|---|
| 20 | 20 | ~90% | PASS (10% expected mock failures) |
| 50 | 50 | ~90% | PASS |
| 100 | 100 | ~90% | PASS |
| 200 | 200 | ~90% | PASS |
| Memory growth at 200 | +9 MB | <100 MB | PASS |
| Event chain corruption | None detected | None | PASS |

## 30-Minute Soak Test
| Metric | Value | Threshold | Status |
|---|---|---|---|
| Tasks completed | 893 | — | PASS |
| RSS growth | +9.3 MB | <100 MB | PASS |
| DB size | 3.99 MB | — | PASS |
| WAL size | 3.98 MB | Stable | PASS |

## EventStore Scaling
| Metric | Value |
|---|---|
| Max events tested | 50,000 |
| Append latency per event | 24 µs |
| Query 48K events by type | 589 ms |
| DB size at 50K events | 22.66 MB |

## Phase C Failure Recovery
| Test Area | Tests | Pass | Fail | Gate |
|---|---|---|---|---|
| Provider Chaos | 5 | 5 | 0 | PASS |
| Session Recovery | 6 | 6 | 0 | PASS |
| SQLite Corruption | 4 | 4 | 0 | PASS |
| Sandbox Security | 12 | 12 | 0 | PASS |
| Telemetry Audit | 5 | 5 | 0 | PASS |
| **Total** | **32** | **32** | **0** | **PASS** |

## Full Test Suite
| Component | Count |
|---|---|
| Total tests | 268 |
| Passed | 268 |
| Failed | 0 |
| Suite duration | 170s |

## Known Limitations
1. First-run cold start latency ~1255ms
2. ETDStore is in-memory only (no persistence)
3. CostTracker lacks per-session scoping
4. Model warm-up is fire-and-forget (not guaranteed complete before first task)
5. ETD avg_cost/avg_latency_ms from single execution (no weighted average)
6. Cost Dashboard spec-only (not implemented)
7. Max tested concurrency: 200 tasks
8. No container-level sandbox isolation
