# Recovery Architecture Proposal

## Recovery Flow

1. Load session record by session id.
2. Validate canonical workspace path ownership.
3. Scan rollouts newest-first.
4. Promote valid `preparing` rollouts to `ready`.
5. Mark missing or invalid rollouts as `abandoned` or `corrupted`.
6. Repoint the active rollout to the newest valid checkpoint.
7. Fall back to empty state only when no valid checkpoint exists.

## Repair Behavior

- Stale pointer: automatically repointed to the newest valid rollout.
- Interrupted write before publish: rollout remains `preparing`, then becomes `abandoned`.
- Interrupted write after publish but before metadata finalize: rollout is promoted during recovery.
- Corrupt snapshot: rollout is marked `corrupted` and skipped.

## Operator Visibility

Every repair action is recorded in `repair_log`, so recovery is not silent.
