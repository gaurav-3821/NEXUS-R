# NEXUS-R Phase 1 Architecture

## Goal

Deliver a local-first agent runtime that can execute bounded natural-language workspace tasks with full auditability and conservative cost controls.

## Subsystems

1. Input Gateway: parse user input into normalized task intent and parameters.
2. Cognition Router: select a local or BYOK model tier using Phase 1 heuristics.
3. Execution Sandbox: execute allowed filesystem and terminal actions within the workspace root.
4. State Core: persist append-only events and maintain in-memory working state.
5. Session Manager: persist crash-safe working-state checkpoints and resume metadata.
6. Workflow Engine: record causal traces for every execution step.
7. Trust Layer: enforce T1-T2 permissions, track cost, and store secrets.

## Execution Flow

1. CLI receives a raw task string.
2. Input Gateway parses the task into an `IntentResult`.
3. Trust Layer checks permission tier and action allowlist.
4. Cognition Router decides `local` or `byok`.
5. Execution Sandbox performs the action in the workspace.
6. Workflow Engine records the causal step chain.
7. Session Manager checkpoints resumable runtime state.
8. State Core appends all events and exposes history/cost views.

## Phase 1 Limits

- Only T1 and T2 are implemented.
- T3 and T4 requests are denied by default.
- Browser automation is not available.
- ETD extraction is not available.
- Authenticated browser/session management is not implemented yet; only runtime checkpointing exists.

## Reserved Extension Points

- `modules/session_manager/`: authenticated session storage and validation extensions build on the runtime checkpoint layer.
- `modules/execution_sandbox/browser_sandbox.py`: Phase 3 browser execution.
- `modules/web_ui/`: Phase 2 dashboard.
- `modules/api_gateway/`: Phase 4 external API.
