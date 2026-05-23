# Execution Sandbox Phase 1 Specification

## Responsibilities

- Execute bounded workspace tasks safely.
- Enforce workspace-root confinement.
- Log every tool invocation and result.

## Supported Tools

- Filesystem list
- Filesystem read
- Filesystem write/append
- Text search
- Restricted terminal execution

## Constraints

- No browser execution in Phase 1.
- No external file access outside workspace root.
- No destructive shell commands.
- Terminal commands must be restricted to an allowlist.
- Docker execution is optional; subprocess fallback is required.
