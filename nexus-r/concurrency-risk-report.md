# Concurrency Risk Report

## Original Risks

- `EventStore` only serialized writes inside one process.
- `WorkingStateStore` was process-local and could not survive crashes.
- There was no session-level coordination for concurrent resume or checkpoint flows.

## Current Mitigations

- Session mutations use SQLite `BEGIN IMMEDIATE` transactions.
- Checkpoint sequence allocation is serialized and unique per session.
- Active-session switches are transactional.
- Resume repairs stale pointers instead of trusting the last raw reference.

## Remaining Risks

- Event persistence and session persistence are still separate stores.
- Cross-store atomicity between event append and session checkpoint is best-effort, not a distributed transaction.
- The identity store still needs the same atomic-write and corruption-handling treatment.
