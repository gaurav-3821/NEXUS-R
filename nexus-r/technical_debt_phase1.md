# Technical Debt Register

## Highest Priority Debt

### 1. BYOK path is architected but unproven

- SecretRegistry is now wired into model selection.
- The missing debt item is operational proof, not code structure.
- Phase 2 should not assume real fallback-to-BYOK works until a live provider key is validated.

### 2. EventStore synchronous append still misses the hard target

- Batch writes are excellent.
- Single-event append is still slightly above target on this hardware.
- The runtime still emits many single events in the task hot path.

### 3. Orchestrator remains too centralized

- It now has better telemetry and clearer provider/event boundaries.
- It is still the place where parsing, permissioning, routing, execution, persistence, and session checkpointing all meet.

## Medium Priority Debt

### 4. Provider failure semantics are too generic

- Some forced failure modes currently collapse into broad runtime errors instead of high-fidelity provider diagnostics.
- This weakens operator trust during incident analysis.

### 5. Package/import shims remain awkward

- `foundation/nexus_r` plus the top-level `nexus_r` shim still creates maintenance drag.
- The new telemetry shim is another symptom of that structure.

### 6. Synthetic local cost accounting

- Local costs are still configuration-derived, not metered from actual runtime resource use.
- They are useful for budget gating, not for truthful accounting.

## Lower Priority Debt

### 7. Session-management artifacts exist ahead of scope

- The repo contains session-related code and reports that were not requested for Phase 1.
- Even if dormant, this increases cognitive load and review noise.

### 8. Heuristic parser growth

- Classification and parameter extraction are still regex-heavy and will become harder to reason about with more task shapes.

## Debt That Should Be Paid Before Phase 2

1. Real BYOK validation with one live provider.
2. Better provider error taxonomy and retry reporting.
3. A decision on whether EventStore hot-path writes stay synchronous or move to a more explicit buffered architecture.
4. Orchestrator decomposition before dashboard/API work expands the integration surface further.
