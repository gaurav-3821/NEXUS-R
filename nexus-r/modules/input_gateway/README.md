Input Gateway module contract:
1. Accept raw user task text.
2. Normalize whitespace and casing conservatively.
3. Identify bounded workspace task type.
4. Estimate task complexity deterministically.
5. Extract parameters for filesystem and terminal actions.
6. Never crash on malformed input.
7. Preserve original text for audit.
8. Avoid model calls in Phase 1.
9. Return unsupported tasks as `unknown`.
10. Emit structures compatible with `nexus_r.events`.
