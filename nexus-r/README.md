# NEXUS-R

NEXUS-R is a personal agent runtime that executes natural-language tasks through a conservative, auditable pipeline.

Phase 1 scope in this repository:

- CLI entry point for task execution
- Input Gateway for intent parsing and parameter extraction
- Basic 2-tier Cognition Router (local vs BYOK)
- Execution Sandbox for workspace-scoped terminal and filesystem actions
- State Core with SQLite-backed event sourcing
- Session Manager with crash-safe runtime checkpoints
- Trust Layer with T1-T2 auto-approval, audit logging, and cost tracking
- Workflow Engine trace recording only

Deferred by design:

- Browser automation
- ETD distillation/reuse
- Web UI
- T3-T4 approvals
- Authenticated browser/session management implementation

The architecture reserves `modules/session_manager/` for the Phase 3 authenticated-session extension.
