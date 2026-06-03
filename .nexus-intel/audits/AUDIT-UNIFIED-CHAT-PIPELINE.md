# AUDIT: Unified Chat Pipeline

- Audit: Unified pipeline `_prepare_intent()` refactor — shared intent preparation for `send_message` and `stream_message`
- Auditor: OpenCode (source-level verification)
- Date: 2026-06-02
- Verdict: `Pass With Risks`

## Scope Reviewed

- `nexus-r/modules/web_ui/src/chat_handler.py` — full file (1082 lines)
- `nexus-r/foundation/nexus_r/model_registry.py` — `provider_chain()`, `_invoke()`, `_invoke_stream()`, `_litellm_completion()`
- `nexus-r/modules/web_ui/src/app.py` — `/api/v1/chat/stream` endpoint
- Git diff: `chat_handler.py` (+117/-? lines), `model_registry.py` (+79/-? lines), `app.py` (+168/-? lines)
- Previous audit: `.nexus-intel/audits/AUDIT-STREAMING-PIPELINE.md`
- Prior failures register: empty

## Acceptance Criteria

| ID | Status | Evidence |
| --- | --- | --- |
| AC-1: `_prepare_intent()` called by `send_message()` | **Verified** | `chat_handler.py:468`: `send_message` awaits `_prepare_intent(...)` as first line |
| AC-2: `_prepare_intent()` called by `stream_message()` | **Verified** | `chat_handler.py:533`: `stream_message` awaits `_prepare_intent(...)` as first line |
| AC-3: Browser requests still work (both paths) | **Verified** | `_prepare_intent()` parses browser intents (lines 140–251). `send_message` delegates to `_stream_response` which runs the browser action loop (line 694+). `stream_message` does NOT run the action loop — pre-existing gap, not a regression. |
| AC-4: Calculator requests still work | **Verified** | `_prepare_intent()` line 82–103 returns early. Both callers handle the `early_res` tuple. |
| AC-5: Memory commands still work | **Verified** | `_prepare_intent()` lines 105–138. Same pattern. |
| AC-6: Forecaster still works | **Verified** | `_prepare_intent()` lines 192–245. Injects forecast data into message. Both paths proceed to LLM with enhanced prompt. |
| AC-7: Trust layer still executes | **Verified** | `_prepare_intent()` lines 286–305 checks `self.perms`. Blocked messages returned via `early_res`. |
| AC-8: Vision fallback still executes | **Verified** | `_prepare_intent()` lines 414–455. Runs for images when model lacks vision. `stream_callback` hook exists but is never connected. |
| AC-9: SSE responses remain valid | **Verified** | `stream_message` emits `status: routing` → `status: thinking` → `token*` → `done` for normal path. Early exits emit `status: routing` → `token` → `done`. Error path emits `error` event. |
| AC-10: TerminalResponse early exits correct as SSE | **Verified** | Calculator, memory, trust-blocked: all three early-return paths yield valid SSE events (lines 537–542). |

## Commands Run

| Command | Result |
| --- | --- |
| `grep -r 'chat/stream|stream_message|_prepare_intent' tests/` | Zero matches — no test coverage for the unified pipeline |
| `git diff HEAD -- chat_handler.py` | `_prepare_intent` extracted, both callers wired, `stream_message` rewritten |
| `git diff HEAD -- model_registry.py` | `provider_chain` handles explicit model names; `_invoke`/`_invoke_stream` handle ephemeral providers; `keep_alive=-1` added |

## Findings

### Severity: High

| Severity | Finding | Evidence | Required action |
| --- | --- | --- | --- |
| **High** | **F1: Latency is ~0ms in `stream_message`** | `chat_handler.py:560`: `started = datetime.now(timezone.utc)` is set *after* the `done` event is yielded and the full stream is complete. Then `_log_response` at line 561–567 computes `(now - started) * 1000` which will be near-zero. The latency stored in the event store is always ~0ms for every SSE-streamed response. Compare with `send_message` line 474 where `started` is set *before* any generation. | Move `started = datetime.now(timezone.utc)` to before `router.stream()` at line 548, or capture the start time at the top of `_prepare_intent`. |
| **High** | **F2: Zero test coverage for unified pipeline** | `grep` found no test references to `_prepare_intent`, `stream_message`, or `/api/v1/chat/stream`. The refactor extracted ~300 lines of shared logic but has no regression tests. | Add unit test for `_prepare_intent` early exits (calculator, memory, trust-blocked) and integration test for `/api/v1/chat/stream` endpoint. |

### Severity: Medium

| Severity | Finding | Evidence | Required action |
| --- | --- | --- | --- |
| **Medium** | **F3: `stream_callback` is never connected** | `_prepare_intent` signature (line 62) accepts `stream_callback`. Lines 437–439 call it during vision fallback to emit `analyzing image` status. But both `send_message` (line 468) and `stream_message` (line 533) pass `None` (the default). SSE users never see the vision status update. | In `stream_message`, pass a wrapper callback that enqueues the SSE event into the async generator (or simply remove the dead callback code and hardcode the SSE yield). |
| **Medium** | **F4: Dead code: `_mock_completion` call in `_invoke`** | `model_registry.py:714–715`: `if provider.uses_mock: return await self._mock_completion(...)`. Method was deleted in commit 9b6ef9b. Currently unreachable (no provider has `uses_mock=True`), but will crash with `AttributeError` if triggered. (Carried forward from pre-refactor.) | Remove the dead branch. |
| **Medium** | **F5: Trust-blocked SSE `done` event has empty `model`** | `_prepare_intent` returns `preferred = ""` for the trust-block case (line 305). `stream_message` emits `{..., 'model': ''}` in the `done` event. Calculator and memory paths use `"calculator"` and `"memory_parser"`. | Use the actual blocked-model value or a sentinel like `"trust_blocked"` instead of empty string. |

### Severity: Low

| Severity | Finding | Evidence | Required action |
| --- | --- | --- | --- |
| **Low** | **F6: Browser action loop absent from SSE path** | `_stream_response` (line 694+) has a 6-step browser action loop. `stream_message` (line 548) just iterates `router.stream()` once. Pre-existing gap — not a regression from this refactor, but the gap is permanent unless the SSE path is upgraded. | Consider extracting the browser action loop from `_stream_response` into a shared method or adding a note in `RISKS.md`. |
| **Low** | **F7: `sendChat` remains dead frontend code** | Imported in `useAppStore.ts` but never called. Only `streamChat` is used. (Carried forward from previous audit.) | Remove unused export. |

## Scope Drift Check

- Unapproved changes found: This was a direct audit request without a task contract.
- Documentation aligned with observed behavior: No documentation for the unified pipeline was found to compare against.

## Remaining Risks

1. **`stream_callback` design is incomplete**: The parameter exists in `_prepare_intent` but cannot be used correctly with async generators (can't `yield` from a callback). Any future attempt to connect it will require a queue-based approach. The current dead code should either be removed or replaced with a working queue.
2. **Ephemeral providers created with `is_available=True` unconditionally** (`model_registry.py:196`): An explicitly requested model that doesn't exist will fall back through the chain, but the error may confuse users.
3. **`keep_alive=-1`** (`model_registry.py:850,910`): Ollama models will stay loaded in memory indefinitely. On memory-constrained systems this could cause OOM. Should be configurable.
4. **No active task contract**: Without an approved task, there is no baseline to measure feature scope against.

## Auditor Notes

The refactoring correctly extracts `_prepare_intent()` as a shared method and both callers are properly wired. The critical pre-existing gaps (no browser action loop in SSE, dead `_mock_completion` code) are not new regressions.

**The one genuine new bug is F1**: `started` is set after streaming completes, making every `stream_message` response record ~0ms latency. This directly corrupts observability data in the event store and cost dashboard.

The test coverage gap (F2) is also concerning: a 117-line change to the core chat pipeline with zero new tests.

**Verdict: Pass With Risks** — the refactoring is architecturally sound but has one observable data-corruption bug (F1) and perpetuates pre-existing gaps without addressing them.
