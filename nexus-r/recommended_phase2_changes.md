# Recommended Changes Before Phase 2

## Do Not Start Phase 2 Until These Are Addressed

### 1. Introduce a real model execution adapter

- Add a dedicated provider layer that actually calls local and BYOK models.
- Route through it from the orchestrator.
- Make timeout, malformed-response, retry, and cost-recording behavior explicit.

### 2. Move provider secret access behind SecretRegistry

- Stop using environment inspection in `ModelRegistry` as the operational secret boundary.
- Environment variables can remain a bootstrap source, not the runtime source of truth.

### 3. Redesign event persistence for sustained writes

- Use a long-lived writer connection, append queue, or explicit batching.
- Keep the append-only audit model, but remove per-event connection churn.

### 4. Break the orchestrator into pipeline stages

- Parser stage
- Permission stage
- Routing stage
- Execution stage
- Persistence stage
- This will reduce Phase 2 blast radius.

### 5. Harden identity/session-adjacent storage before adding browser auth later

- Store encryption keys outside the same directory as ciphertext.
- Add corruption handling that returns a typed failure instead of crashing on invalid tokens.

## Recommended, But Not Blocking

1. Clean up package layout and remove shim duplication.
2. Replace heuristic parser growth with a more structured task schema strategy.
3. Add benchmark thresholds to CI.
4. Add lock-contention and persistence-degradation tests to the permanent test suite.
