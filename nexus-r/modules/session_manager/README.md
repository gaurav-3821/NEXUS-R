Session Manager now provides the runtime session foundation.

Current scope:
- durable workspace-scoped session catalog
- immutable rollout snapshots with atomic replace
- stale-pointer detection and repair
- canonical workspace-path validation
- crash-safe resume flow for working-state checkpoints

Still deferred:
- browser-auth session storage
- cookie injection
- CLI auth management
