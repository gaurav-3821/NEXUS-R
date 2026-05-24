# Workflow Engine Phase 2 Specification

## Responsibilities

- Full ETD (Execution Trace Database) 7-stage pipeline.
- Store and retrieve ETD entries with a structured JSON schema.
- Rank retrieval results by relevance using a scoring algorithm.
- Invalidate stale or low-quality ETD entries.
- Continue producing causal traces for every execution step.

## Phase 2 Scope

- ETD extraction, generalization, replay
- ETD entry JSON schema and storage
- Retrieval ranking with configurable weights
- Invalidation triggers (time, failure rate, manual)

## ETD 7-Stage Pipeline

```
Stage 1: RECORD   — Capture raw trace at execution time
Stage 2: EXTRACT  — Select candidate traces (successful, high-confidence)
Stage 3: GENERALIZE — Parameterize literals (paths, filenames, IDs)
Stage 4: VERIFY   — Replay generalized trace in sandbox; confirm pass/fail
Stage 5: INDEX    — Write verified ETD entry with embedding and tags
Stage 6: RETRIEVE — On new task, rank matching ETDs by similarity
Stage 7: INVALIDATE — Mark entries stale by age, failure rate, or manual purge
```

```python
class ETDPipeline:
    async def record_trace(self, trace: list[CausalEvent]) -> str: ...
    async def extract_candidates(self) -> list[list[CausalEvent]]: ...
    async def generalize(self, trace: list[CausalEvent]) -> GeneralizedTrace: ...
    async def verify(self, generalized: GeneralizedTrace) -> VerificationResult: ...
    async def index(self, entry: ETDEntry) -> str: ...
    async def retrieve(self, query: RetrievalQuery) -> list[RankedETDEntry]: ...
    async def invalidate(self, entry_id: str, reason: str) -> None: ...
```

## ETD Entry JSON Schema

```json
{
  "$schema": "https://nexus-r.ai/etd-entry-v1",
  "type": "object",
  "required": ["entry_id", "trace", "generalized_input", "action_type",
               "tier_used", "verification", "created_at", "ttl_days"],
  "properties": {
    "entry_id": {"type": "string", "format": "uuid"},
    "trace": {
      "type": "array",
      "items": {"$ref": "#/definitions/causal_event"}
    },
    "generalized_input": {"type": "string"},
    "action_type": {"type": "string"},
    "parameters": {
      "type": "object",
      "properties": {
        "literal_placeholders": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "placeholder": {"type": "string"},
              "original": {"type": "string"},
              "replacement": {"type": "string"}
            }
          }
        }
      }
    },
    "tier_used": {"type": "string", "enum": ["T1", "T2", "T3", "T4", "T5", "T6"]},
    "embedding": {"type": "array", "items": {"type": "number"}},
    "tags": {"type": "array", "items": {"type": "string"}},
    "verification": {
      "type": "object",
      "properties": {
        "status": {"type": "string", "enum": ["passed", "failed", "unverified"]},
        "verified_at": {"type": "string", "format": "date-time"},
        "latency_ms": {"type": "number"}
      }
    },
    "created_at": {"type": "string", "format": "date-time"},
    "ttl_days": {"type": "integer", "minimum": 1},
    "hit_count": {"type": "integer", "minimum": 0},
    "last_hit_at": {"type": "string", "format": "date-time"}
  }
}
```

## Retrieval Ranking Algorithm

Given a query `(normalized_input, action_type, parameters)` and a set of
candidate ETD entries, rank by:

```
score = w1 * text_similarity + w2 * type_match + w3 * recency - w4 * staleness
```

where:

| Weight | Default | Source |
|--------|---------|--------|
| w1 | 0.50 | Cosine similarity of embedding vectors |
| w2 | 0.25 | Exact action_type match: 1.0 if match, 0.0 otherwise |
| w3 | 0.15 | `1.0 - min(days_since_creation / ttl_days, 1.0)` |
| w4 | 0.10 | `hit_count == 0 ? 0.1 : 0.0` (penalty for unused entries) |

```python
class RetrievalQuery:
    normalized_input: str
    action_type: str
    parameters: dict[str, object]
    max_results: int = 10
    min_score: float = 0.3
```

```python
class RankedETDEntry:
    entry: ETDEntry
    score: float
    matched_fields: list[str]
```

## Invalidation Triggers

1. **Time-based**: entry `ttl_days` exceeded → auto-invalidate on retrieval.
2. **Failure cascade**: entry replayed and failed verification 3+ consecutive
   times with the same action_type → invalidate.
3. **Manual purge**: `POST /admin/etd/invalidate/{entry_id}`.
4. **Staleness**: `hit_count == 0` for 30+ days → deprioritize (score penalty),
   then invalidate at 60 days.

```python
class ETDInvalidationRule:
    rule_id: str
    trigger: str  # "ttl_exceeded" | "failure_cascade" | "manual" | "stale_zero_hit"
    entry_ids: list[str]
    invalidated_at: str
    reason: str
```

## Error Codes (WE-031 to WE-100)

| Code  | Condition | Message |
|-------|-----------|---------|
| WE-031 | ETD entry quota exceeded | "ETD entry limit ({max}) reached. Drop oldest or increase quota." |
| WE-032 | Generalization failed | "Could not generalize trace {trace_id}: {reason}" |
| WE-033 | Verification replay failed | "Replay failed for generalized trace: {error}" |
| WE-034 | ETD entry not found | "No ETD entry found for entry_id {entry_id}" |
| WE-035 | Embedding generation failed | "Embedding generation failed for trace {trace_id}: {error}" |
| WE-036 | Retrieval returned zero results | "No matching ETD entries for query (min_score={min_score})" |
| WE-037 | ETD index write failure | "Failed to write ETD entry {entry_id}: {error}" |
| WE-038 | Invalidation rule conflict | "Entry {entry_id} already invalidated by rule {rule_id}" |
| WE-039 | Pipeline stage timeout | "Stage {stage_name} exceeded timeout {timeout}s for trace {trace_id}" |
| WE-040 | Quota limit reached | "ETD pipeline capacity reached. Retry after compact or quota increase." |
| WE-041–WE-100 | Reserved | Reserved for sub-features (e.g., multi-modal ETD, cross-session) |

## Validation Protocol

ETD correctness is validated with **10 task variants**: 5 used for learning
(record → extract → generalize → index) and 5 held back for checking
(retrieve → verify score ≥ 0.7 on all 5). A variant is a distinct combination
of `(action_type, normalized_input, parameters)`.

## Test Scenarios (Phase 2)

```
Given a completed task trace with 8 causal events
When extract_candidates() runs
Then it returns the trace (success=True, confidence > 0.8)

Given a generalized trace with parameterized paths
When verify() replays in sandbox
Then verification result is "passed"

Given an ETD entry with embedding [0.1, 0.3, ...]
When retrieve(query) is called with similar input
Then result includes the entry with score >= 0.7

Given an ETD entry past its ttl_days
When retrieve() runs
Then entry is invalidated and excluded from results
```
