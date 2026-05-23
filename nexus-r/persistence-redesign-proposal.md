# Persistence Redesign Proposal

## New Model

Use two layers:

1. SQLite session catalog for session rows, rollout metadata, active pointers, and repair logs.
2. Immutable snapshot files for working-state checkpoints.

## Guarantees

- SQLite transaction boundaries protect pointer and metadata mutation.
- Snapshot files are atomically published with `os.replace`.
- A rollout cannot become active until its snapshot exists.
- A snapshot file path is derived from session id and sequence, not stored as an arbitrary absolute pointer.
- Resume always validates the snapshot hash before trusting it.

## Why This Fixes the Original Risk

The prior design had durable events but no durable resumable state. The new design makes state recovery explicit, inspectable, and repairable without overloading the event log.
