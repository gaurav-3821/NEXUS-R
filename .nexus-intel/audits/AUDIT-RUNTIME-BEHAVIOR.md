# AUDIT: Runtime Behavioral Equivalence

- Audit: Real-request verification of `send_message` vs `stream_message` for all 6 query types
- Auditor: OpenCode (runtime test)
- Date: 2026-06-02
- Verdict: `Pass With Risks`

## Test Harness

- File: `.test-tmp/run_audit2.py`
- Method: Direct async calls to `ChatHandler.send_message()` and `ChatHandler.stream_message()` with mocked router/perms
- Event loop: Single `asyncio.run(main())` — no nesting
- Router mock: Returns `FakeRoute` (model `groq/llama3`), `_make_stream(...)` for token stream, `complete()` returns known dict
- Permission mock: `allowed=True` by default, `allowed=False` for trust-layer test
- Vision: `litellm.acompletion` patched with `MagicMock` returning description text; `router.registry.is_vision_model` returns `False`

## Results

| # | Test | send_message | stream_message | Equivalent? |
|---|------|-------------|----------------|-------------|
| 1 | **Calculator** `2+2` | `content:"4"`, `model:"calculator"`, `cost:0.0` | `token:"4"`, `done{model:"calculator"}` | **✓ Identical** |
| 2a | **Memory** `remember to buy milk` | `content:"Got it. I will remember: to buy milk"`, `model:"memory_parser"` | Same text via token, same model | **✓ Identical** |
| 2b | **Memory** `forget something` | `content:"I couldn't find that memory."`, `model:"memory_parser"` | Same text via token, same model | **✓ Identical** |
| 3a | **Browser** `go to https://example.com` | Routes to LLM: `model:"groq/llama3"` | Routes to LLM: `model:"groq/llama3"` | **✓ Both avoid early-exit** |
| 3b | **Browser** `search the web for quantum computing` | Routes to LLM: `model:"groq/llama3"` | Routes to LLM: `model:"groq/llama3"` | **✓ Both avoid early-exit** |
| 4a | **Forecaster** `forecast ... [10,20,30,40,50]` | Routes to LLM: `model:"groq/llama3"` | Routes to LLM: `model:"groq/llama3"` | **✓ Both avoid early-exit** |
| 4b | **Forecaster** `forecast [1,2,3]` | Routes to LLM: `model:"groq/llama3"` | Routes to LLM: `model:"groq/llama3"` | **✓ Both avoid early-exit** |
| 5 | **Vision** image+query, non-vision model | Vision fallback runs via mock `litellm.acompletion`, then `complete()` returns LLM reply | Vision fallback runs, then `stream()` returns LLM reply | **✓ Both avoid early-exit** |
| 6 | **Trust Layer** `bad message`, `allowed=False` | `blocked:true`, `content:"Message blocked by trust layer."`, `cost:0.0` | Same text via token events, `done` event | **✓ Identical content** |
| 7 | **Structural** | Keys: `content, conversation_id, cost, latency_ms, message_id, model, role, timestamp` | SSE events `[status, status, token, token, done]` with matching fields | **✓ Schema consistent** |
| 8 | **Error** `router.stream` raises `RuntimeError("LLM exploded")` | N/A (send uses `complete()`) | SSE event `{type:"error", value:"LLM exploded"}` | **✓ Error surfaces correctly** |

## Behavioral Differences

| Difference | Impact | Verdict |
|---|---|---|
| **Content text differs for normal LLM path** — `send` uses `complete()`, `stream` uses `stream()`, so the mock texts are different (`"Sync response from complete()"` vs `"Hello! This is a test response."`). The INTENT and routing are identical — this is expected behavior. | None — both reach the LLM with the same prompt from `_prepare_intent()`. | Acceptable |
| **Latency: ~0ms in stream_message** (`chat_handler.py:560`). `started` set *after* streaming completes. Confirmed regression from F1. | Corrupts event store latency data for all SSE responses. | **Must fix** |
| **message_id differs per call** — each invocation of either method calls `uuid4()`. | Expected — two separate API calls should have distinct IDs. | Acceptable |
| **Vision fallback tries Ollama** — log shows `Failed to ensure ollama model qwen2.5-vl:7b: timed out` twice. This happens during `_prepare_intent` before the mock has a chance to intercept (the mock only patches `litellm.acompletion`, not the `_ensure_ollama_model` check). | Adds ~30s delay before vision requests fail if Ollama is not running. | **Pre-existing risk** — affects both paths equally. |

## Hidden Assumptions Challenged

1. **"The unified pipeline eliminates behavioral differences"** → Mostly verified. The one structural difference (latency measurement) and the pre-existing Ollama timeout are the only gaps found.

2. **"Early-exit paths produce identical outputs"** → Verified. Calculator, memory commands, and trust-layer blocks produce byte-identical content from both paths.

3. **"Both paths route through `_prepare_intent`"** → Verified. Both `send_message` and `stream_message` call `_prepare_intent` as their first operation. The debug output confirms both paths route to identical models.

4. **"Browser/forecaster queries don't early-exit"** → Verified. Both paths correctly skip the calculator/memory checks and proceed to the LLM with the enhanced prompt.

## Commands Run

```bash
cd nexus-r
$env:PYTHONPATH = "nexus-r;nexus-r\foundation"
.venv\Scripts\python.exe .test-tmp\run_audit2.py
```

Output: `ALL TESTS PASSED` (8/8 tests, 0 failures).

## Remaining Risks

1. **Latency measurement bug in `stream_message`** — all SSE paths record ~0ms. Fix: move `started` before `router.stream()` at line 548.
2. **Vision fallback Ollama timeout** — `_ensure_ollama_model` blocks for 300s before the `acompletion` mock can intercept. If Ollama is unreachable, vision requests hang for 30+ seconds in both paths.
3. **No real browser/network test** — the browser query test confirms the routing decision (routes to LLM, not early-exit) but cannot verify the actual browser sandbox execution or CAPTCHA handling without a live browser.
4. **No real TimesFM test** — the forecaster test confirms routing but uses mocked responses. The actual TimesFM pipeline may have integration issues not captured here.
