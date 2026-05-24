# Cognition Router Phase 2 Specification

## Responsibilities

- Route tasks across a 6-tier fallback chain (T1-T4 + frontier).
- Run parallel probe requests to estimate provider latency and availability.
- Learn de-escalation patterns from prior trace outcomes.
- Estimate cost and latency before execution.

## Phase 2 Extensions

### 6-Tier Fallback Chain

```
T1/local     → ollama/qwen2.5:1.5b-instruct
T2/byok      → groq/llama-3.3-70b-versatile
T3/premium   → groq/mixtral-8x7b-32768 or openai/gpt-4o-mini
T4/frontier  → anthropic/claude-sonnet-4-20250514 or openai/gpt-4o
T5/enterprise → anthropic/claude-opus-4-20250514 or openai/o3
T6/custom    → user-registered model URI
```

Routing decisions use the `complexity_score` from the intent parser:

| Score Range | Default Tier | Fallback Chain |
|-------------|-------------|----------------|
| 0.0–0.3     | T1          | T1 → T2 → mock |
| 0.3–0.5     | T2          | T2 → T3 → T1 → mock |
| 0.5–0.75    | T3          | T3 → T4 → T2 → mock |
| 0.75–0.9    | T4          | T4 → T5 → T3 → mock |
| 0.9–1.0     | T5          | T5 → T6 → T4 → mock |

### Performance Requirement

Routing must complete (including parallel probe) in under **50ms** total.
If probe latency exceeds 50ms, the routing falls back to the static tier
default without waiting for all probe results.

## Parallel Probe

Before routing, dispatch brief probe requests (trivial prompt, 1 token
response) to candidate providers in parallel:

```python
class ProbeResult:
    provider: str
    tier: str
    latency_ms: float
    available: bool
    error: str | None
```

```python
async def probe_all(candidates: list[str]) -> list[ProbeResult]:
    """
    Fire probe requests in parallel.
    Timeout per probe: 3s.
    Returns sorted by latency_ms ascending.
    """
```

Probe results feed into routing: the router prefers the lowest-latency
available provider within the selected tier, not the hard-coded default.

### De-Escalation Learning

After each task completion, the trace result is fed back to update a
per-provider success table:

```python
class TierHistoryEntry:
    task_hash: str
    tier_used: str
    success: bool
    latency_ms: float
    cost: float
    retry_count: int
```

```python
async def record_routing_outcome(entry: TierHistoryEntry) -> None:
    """
    Store in event_store as event_type='routing_outcome'.
    Used by de-escalation to detect:
    - A lower tier consistently succeeds for similar tasks.
    - A higher tier times out or fails repeatedly.
    """
```

De-escalation rule: if a task type has 5+ consecutive successes on tier N
with latency <50% of tier N+1, downgrade the default to tier N for future
similar tasks.

## Error Codes (CR-051 to CR-100)

| Code  | Condition | Message |
|-------|-----------|---------|
| CR-051 | Probe timeout | "Probe timed out for {provider} after 3s" |
| CR-052 | All probes failed | "All probed providers unreachable" |
| CR-053 | Tier N+1 unavailable, staying at N | "Requested tier {n+1} unavailable, using {n}" |
| CR-054 | De-escalation triggered | "De-escalated from {n+1} to {n} based on {k} recent successes" |
| CR-055 | De-escalation table full | "De-escalation table at capacity ({max} entries), dropping oldest" |
| CR-056 | Provider chain dedup removed all | "Fallback chain empty after deduplication" |
| CR-057 | Probe returned latency > threshold | "Probe latency {ms}ms exceeds threshold {threshold}ms for {provider}" |
| CR-058 | Complexity below tier floor | "Complexity {score} below minimum {min} for tier {name}" |
| CR-059 | No matching tier in config | "No tier configuration found for complexity {score}" |
| CR-060 | De-escalation table read error | "Failed to read de-escalation history: {error}" |
| CR-061–CR-100 | Reserved | Reserved for future sub-routes (e.g., vision, code, audio) |

## Test Scenarios (Phase 2)

```
Given a task with complexity 0.8
When router.probe_all([groq, openai, anthropic]) returns
Then preferred tier is T4
And the fastest probed provider is selected within T4

Given 5 "summarize" tasks completed successfully on T3
When a new "summarize" task arrives with complexity 0.7
Then de-escalation lowers default from T4 to T3
And rationale includes "de-escalated_from_T4"

Given all probes fail
When route() is called
Then error CR-052 is raised
And fallback chain falls through to mock
```
