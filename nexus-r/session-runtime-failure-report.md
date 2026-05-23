# Session Runtime Failure Report

## Root Cause

The original runtime had no durable session model. It persisted events to SQLite, kept working state only in process memory, and stored an unrelated encrypted identity blob in the same state directory. That architecture creates stale session-path failures because any future resume mechanism would have to reconstruct session state from loosely related files without a transactional source of truth.

## Findings

- Stale session paths occur when metadata points at filesystem state that is not canonically owned by a durable session record.
- Concurrency was unsafe across processes because the only protection was an in-process async lock inside `EventStore`.
- File rotation and snapshots were unsafe because there were no immutable checkpoints, no pointer invalidation, and no repair contract.
- The event/session model was too tightly coupled in the opposite way: events existed, but resumable session state did not. Any resume layer built later would have to guess from events.
- Windows path handling was a contributor because the previous design stored raw paths only; no canonicalization existed for case, separator, or relative-path normalization.

## Architectural Correction

- Added `SessionManager` as a real runtime subsystem.
- Session metadata is now transactional in SQLite.
- Rollout snapshots are immutable JSON files written with temp-file replace plus fsync.
- Active session pointers are repaired automatically if they become stale, corrupted, or incomplete.
- Resume validates canonical workspace ownership before loading state.
