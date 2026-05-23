# Phase 1 Security Report

## Executive Summary

Phase 1 is safer than the initial scaffold, but it is still development-grade security, not production-grade security. The sandbox boundary is meaningful for current supported commands, yet several core trust assumptions remain weak or incomplete.

## Security Findings

### High: BYOK secret handling is not integrated into the actual routing path

- `foundation/nexus_r/model_registry.py:35-45` reads provider availability straight from environment variables.
- `modules/trust_layer/src/secret_registry.py:12-44` exists, but the core router/model path does not use it.
- Impact: the advertised secret-storage layer is not the actual control plane for provider access.

### High: Real provider failure modes cannot be security-tested because provider execution does not exist

- There is no real `litellm` request path in the runtime.
- Provider timeout and malformed-response injection were impossible in `scripts/phase1_failure_injection.py`.
- Impact: provider hardening is effectively untested because the provider boundary is still missing.

### Medium: IdentityStore keeps the encryption key beside the ciphertext

- `modules/state_core/src/identity_store.py:12-20`
- This protects against casual file inspection, not against local compromise of the state directory.
- Failure injection confirmed corrupted ciphertext raises `InvalidToken` and currently crashes the store consumer.

### Medium: Sandbox policy is verb-based, not semantic

- `modules/execution_sandbox/src/sandbox.py:134-168`
- Current allowlist works for the small command set, but policy decisions are still based on command verb plus a few banned metacharacters.
- This is acceptable for Phase 1 only because the command surface is tiny.

### Medium: Database lock handling is graceful at the API boundary but not self-healing

- Failure injection showed `database is locked` is surfaced as task failure instead of caller crash.
- Recovery behavior is now better, but there is no retry queue, no backoff, and no event repair process.

## Prompt Injection Audit

- Current Phase 1 code is mostly not vulnerable to classical prompt injection because no real LLM prompt loop exists.
- That is not a comfort signal. It is a missing-feature signal.
- Once real model execution is added, there is currently no prompt compartmentalization or policy-wrapper infrastructure ready for it.

## Filesystem Boundary Audit

- `modules/execution_sandbox/src/sandbox.py:187-193` enforces workspace-root confinement using resolved paths.
- Path traversal attempts such as `../secret.txt` are blocked.
- This control is good for current local-file operations.

## Subprocess Safety Audit

- Shell chaining/redirection is blocked at `modules/execution_sandbox/src/sandbox.py:138-143`.
- External commands are allowlisted by verb.
- Remaining weakness: if the allowlist expands carelessly later, the current model does not deeply inspect argument semantics.

## SQLite Corruption / Concurrency Audit

- WAL mode and busy timeout are enabled in `foundation/nexus_r/events.py:294-300`.
- Failure injection still reproduced `database is locked`.
- Conclusion: current settings reduce the chance of immediate failure but do not solve contention.

## Trust-Scoring Manipulation Audit

- There is no real trust scoring system yet.
- Complexity scoring and routing are heuristic and local-only.
- Conclusion: manipulation resistance cannot be honestly claimed because the relevant subsystem does not exist yet.

## Honest Verdict

- Critical findings: `0`
- High findings: `2`
- Medium findings: `4`
- Low findings: several prototype-grade gaps

Phase 1 is acceptable for controlled local development. It is not acceptable for production, shared multi-user environments, or any claim of secure BYOK operation.
