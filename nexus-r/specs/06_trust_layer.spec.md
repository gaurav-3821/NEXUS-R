# Trust Layer Phase 1 Specification

## Responsibilities

- Enforce T1-T2 allowlists.
- Deny T3-T4 by default.
- Log every decision.
- Track per-task and aggregate cost.
- Store secrets with a secure-provider-first strategy.

## Tier Rules

- `T1`: read-only workspace inspection and safe queries.
- `T2`: write inside workspace root and restricted terminal commands.
- `T3`: not implemented; deny by default.
- `T4`: not implemented; deny by default.

## Secret Handling

- Prefer OS credential manager via `keyring`.
- Fallback must avoid plaintext persistence.
- Secrets must never be written to event payloads.
