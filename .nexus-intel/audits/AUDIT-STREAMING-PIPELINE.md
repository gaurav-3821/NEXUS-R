# AUDIT: Streaming Pipeline Runtime Audit

- Audit: Streaming pipeline `streamChat()` → `fetch()` → Vite proxy → FastAPI → `chat_handler.stream_message()`
- Auditor: OpenCode (runtime analysis)
- Date: 2026-06-02
- Verdict: `Fail`

## Scope Reviewed

- `nexus-r/frontend/src/api/chat.ts` (line 20–57)
- `nexus-r/frontend/src/api/client.ts` (full)
- `nexus-r/frontend/src/store/useAppStore.ts` (line 135–176)
- `nexus-r/frontend/vite.config.ts` (line 11–17)
- `nexus-r/modules/web_ui/src/app.py` (line 755–775)
- `nexus-r/modules/web_ui/src/chat_handler.py` (line 502–594)
- `nexus-r/foundation/nexus_r/model_registry.py` (line 260–299, 714–715, 763–875)
- `nexus-r/tests/integration/test_chat_api.py`
- `nexus-r/tests/unit/test_chat_handler.py`
- Git status: 40+ modified files, untracked `.nexus-intel/` and new API modules
- Prior failures register: empty — no prior streaming failures recorded
- ASM-0001 (unclear delivery phase) is relevant: `stream_message` may be Phase 2 scaffolding that should have been replaced

## Acceptance Criteria

| ID | Status | Evidence |
| --- | --- | --- |
| HTTP status codes are correct for all error paths | **Failed** | Pre-stream checks (401/403/422/501) are correct, but mid-stream generator crashes produce 200 with truncated content |
| Response payload is correctly formed SSE | **Pass With Risks** | SSE `data:` lines are valid JSON; cost/latency data is emitted *after* the `done` event so frontend never receives it |
| Stream delivers tokens incrementally | **Pass** | `router.stream()` yields `ModelStreamChunk` objects; `stream_message` wraps each as `{"type":"token","value":"..."}` |
| Exceptions are caught and surfaced | **Failed** | `RuntimeError` from routing is caught and yields `error` event; all other exceptions crash the generator silently |
| `stream_message` has feature parity with `send_message` | **Failed** | `stream_message` omits calculator, memory commands, browser intents, forecasting, permission check, vision fallback, artifact/browser instructions, pattern extraction, memory extraction, and telemetry |
| Frontend SSE parser handles partial reads | **Pass With Risks** | `split('\n')` assumes line boundaries; partial lines are silently dropped in the `try/catch` |

## Commands Run

| Command | Result |
| --- | --- |
| grep for 'chat/stream' in tests/ | No matches — zero integration test coverage for the SSE endpoint |
| grep for 'uses_mock.*True' | No matches — `uses_mock` defaults to `False` everywhere; the `_mock_completion` call at line 715 is dead code |
| grep for 'sendChat[^S]' in frontend/src/ | `sendChat` is imported in `useAppStore.ts` but never called — only `streamChat` is used |

## Findings

### Severity: Critical

| Finding | Evidence | Required action |
| --- | --- | --- |
| **F1: `stream_message` is a degraded reimplementation of `send_message`** | `stream_message` (chat_handler.py:502) has none of: calculator bypass (line 81), memory commands (line 104), browser intents (line 139), forecasting (line 193), permission check (line 288), vision fallback (line 419), artifact/browser prompt injection (line 321/357), pattern/memory extraction (line 489/493), telemetry (line 496). `send_message` has all of these. | Either port all features to `stream_message` or route SSE requests through `send_message` → `_stream_response` and convert WS broadcasts to SSE yields. |
| **F2: Mid-stream exceptions cause silent truncation** | If `stream_message` raises after the first `yield`, FastAPI has already sent HTTP 200. The frontend receives a partial stream, exits the `reader.read()` loop when `done` arrives, and shows no error. `useAppStore.ts:178` catch block only fires if `streamChat()` throws, which only happens on non-2xx responses. | Wrap the entire generator body in try/except; yield an `error` SSE event before returning; add a stream-timeout watchdog. |

### Severity: High

| Finding | Evidence | Required action |
| --- | --- | --- |
| **F3: No integration test for `/api/v1/chat/stream`** | `grep -r 'chat/stream' tests/` returned zero results. The `test_chat_api.py` tests only cover `/api/v1/chat` (non-streaming). The unit tests mock `router.stream` but don't exercise the SSE endpoint through `TestClient`. | Add integration test: POST `/api/v1/chat/stream` with `TestClient`, read SSE lines, verify event types and ordering. |
| **F4: Cost/latency emitted after `done` event** | `stream_message` yields the `done` SSE event at line 584, then calls `_log_response` for cost/latency at line 587. The `done` event has no `cost` or `latency_ms` field — contrast with `send_message` which includes these in the response dict. | Include `cost` and `latency_ms` in the `done` event payload. |
| **F5: Dead code: `_invoke` calls removed `_mock_completion`** | model_registry.py:714–715: `if provider.uses_mock: return await self._mock_completion(...)`. Method `_mock_completion` was deleted in commit 9b6ef9b. Currently unreachable (no provider has `uses_mock=True`), but will crash with `AttributeError` if any code path sets it. | Remove the dead branch or restore the mock method. |

### Severity: Medium

| Finding | Evidence | Required action |
| --- | --- | --- |
| **F6: Frontend error detail is lost** | `streamChat` (chat.ts:33) throws `new Error('Stream error: ${response.status}')` — discards server body. A 422 or 401 response may contain useful `detail` in the body. | Include response body text in the error message (similar to `apiPost` in client.ts:47). |
| **F7: SSE parser silently drops partial lines** | `chunk.split('\n')` assumes each `reader.read()` call returns complete lines. If TCP segmentation splits a line, `line.startsWith('data: ')` fails for both fragments. The event is lost silently. | Accumulate incomplete lines across reads; process only when a `\n` terminator is found. |

### Severity: Low

| Finding | Evidence | Required action |
| --- | --- | --- |
| **F8: `sendChat` is dead frontend code** | Imported in `useAppStore.ts` but never called. `sendChatMessage` uses only `streamChat`. | Remove or mark as unused. |
| **F9: No stream timeout** | `stream_message` has no timeout wrapper around `router.stream()`. If the LLM hangs, the SSE connection stays open indefinitely. | Apply `asyncio.wait_for()` with a configurable timeout around `router.stream()`. |

## Scope Drift Check

- Unapproved changes found: No task was defined for this audit (it was a direct request).
- Documentation aligned with observed behavior: No streaming-specific documentation was found to compare against.

## Remaining Risks

1. **Feature drift between SSE and WebSocket paths**: The SSE path avoids the 6-step browser-action loop in `_stream_response`, which is arguably correct (SSE is simpler). But the missing permission check means SSE bypasses the trust layer entirely.
2. **Worktree state**: 40+ modified files plus untracked new modules suggest this is an active development branch. Any fix must account for uncommitted changes.
3. **No active task file**: Without an approved task contract, there is no baseline to measure scope compliance against.

## Auditor Notes

This audit was performed by static source analysis, not by running the application. Runtime verification (launching the app, sending a chat, inspecting the SSE stream with curl) would add certainty. The highest-risk finding is F1: the SSE path is silently feature-incomplete compared to the WebSocket path. If the SSE path is the primary user-facing chat interface (as indicated by `sendChatMessage` calling `streamChat`), this is a critical gap.
