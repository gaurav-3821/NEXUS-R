# Phase 1 Acceptance Criteria

## Functional

- CLI can execute a bounded natural-language task end-to-end.
- Input Gateway produces a valid `IntentResult` for any string input.
- Router selects local or BYOK deterministically from configured conditions.
- Sandbox enforces workspace confinement.
- Event store records a full audit trail for every action.
- Cost summary is queryable.

## Non-Functional

- Tests pass without Ollama, LiteLLM, Docker, or keyring installed.
- T3/T4 requests are denied by default.
- All security-sensitive events redact secrets.

## Gate Targets

- 5 beta users, 20+ tasks each
- >80% success rate
- Average cost < $0.10 for T1-T2
- Full audit trail for every action
