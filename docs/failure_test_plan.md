# Failure Test Plan — Phase C

## Overview

Phase C validates system resilience under failure conditions. All failure tests are in `tests/failure/`.

## Test 1: Provider Interruption (`test_provider_interruption.py`)

**Goal:** Verify graceful fallback when model providers are unavailable.

### Scenarios
- Preferred model (ollama) returns connection refused
- BYOK endpoint returns HTTP 500
- All models in the fallback chain are down
- Mid-stream disconnection during `complete()`

### Expected Behavior
- Router falls through the 6-tier CAR chain to the next available model
- Telemetry records `provider_failure` with provider name and error type
- If all models unavailable, task returns `success=False` with descriptive error
- No unhandled exceptions

### Injection Method
- Monkeypatch `ModelRegistry.complete()` or `ModelInvocationResult` to simulate failures

## Test 2: Sandbox Escape (`test_sandbox_escape.py`)

**Goal:** Verify sandbox confinement cannot be bypassed.

### Scenarios
- Path traversal: `../../etc/passwd`, `..%2f..%2f`, UNC paths
- Shell injection: `; rm -rf /`, `| cmd`, `$(whoami)`, backticks
- Environment leak: `echo %NEXUS_BYOK_API_KEY%`
- Resource abuse: fork bomb, infinite loop, memory exhaustion

### Expected Behavior
- All traversal attempts return `PermissionError` or empty result
- Shell injection characters are escaped via `shlex.quote`
- Environment is sanitized (NEXUS secrets redacted)
- Resource limits kill runaway processes

### Injection Method
- Direct `sandbox.execute()` calls with malicious inputs
- Verify output is safe (no leaked secrets, no files outside workspace)

## Test 3: SQLite Corruption (`test_sqlite_corruption.py`)

**Goal:** Verify EventStore handles database corruption without data loss beyond the corrupted window.

### Scenarios
- Corrupt last N bytes of the WAL file
- Truncate `events` table mid-file
- Delete the WAL file while EventStore is running
- Simulate a failed `PRAGMA journal_mode=WAL`

### Expected Behavior
- EventStore detects corruption on next `initialize()`
- All events before corruption point are readable
- Session recovery skips corrupted events
- Error logged, no crash

### Injection Method
- Direct file manipulation (binary truncation, byte mangling)
- Restart EventStore after corruption
- Verify pre-corruption events are intact

## Test 4: Session Recovery (`test_session_recovery.py`)

**Goal:** Verify session recovery after a crash at any checkpoint.

### Scenarios
- Crash before first checkpoint (no state to recover)
- Crash during `os.replace` of checkpoint pointer (partial write)
- Crash with stale pointer pointing to deleted checkpoint
- Crash with two checkpoints in conflict (concurrent writes)

### Expected Behavior
- Recovery picks the latest valid checkpoint
- Stale pointers are repaired to the previous valid checkpoint
- `session_manager.resume_session()` always returns a consistent state
- Sequence counter is monotonic

### Injection Method
- Manually create/corrupt checkpoint files in `.nexus-r/sessions/`
- Use `os.rename` + `fsync` patterns to create exact crash states
- Verify `resume_session()` behavior for each

## Run Order

1. `test_sandbox_escape` — quick, no infrastructure needed
2. `test_sqlite_corruption` — moderate, file manipulation
3. `test_session_recovery` — moderate, checkpoint manipulation
4. `test_provider_interruption` — quick, monkeypatch

## Pass/Fail Criteria

| Test | Critical Fail | Warning |
|------|--------------|---------|
| Sandbox Escape | Any escape succeeds | Any error not logged |
| SQLite Corruption | Data loss beyond corruption window | Recovery takes >1s |
| Session Recovery | Inconsistent state after recovery | Sequence gap >1 |
| Provider Interruption | Unhandled exception | Fallback >5s |
