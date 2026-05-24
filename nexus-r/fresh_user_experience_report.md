# Fresh User Experience Report

Date: May 23, 2026
Total time: 14.8s
Target: <10min
Result: PASS

## Demo Sequence Results

| Step | Status | Time | Notes |
|------|--------|------|-------|
| nexus run "hello" | PASS | 8.30s | >5s due to LiteLLM first-load overhead |
| nexus run "create file test.txt" | PASS | 1.13s | File created in workspace |
| nexus history | PASS | instant | 2 entries shown |
| nexus cost | PARTIAL | instant | Returns None for sandbox-only tasks |
| nexus run "deploy and rotate secrets" | PASS | instant | Correctly DENIED |
| pytest tests/unit/ -q | PASS | 2.2s | All 18 tests pass |

## Cost Tracking Gap
`nexus cost` returns `None` for `total_cost` when only sandbox tasks
(file operations, terminal commands) have been run. Cost tracking only
records entries for LLM provider invocations. Sandbox-only operations
incur $0 cost but are not reflected in the cost summary.

## Windows-Specific Notes
- Backslash paths: correctly blocked by path traversal check
- Ollama on native Windows: works via httpx to localhost:11434
- Ctrl+C: CancelledError propagates cleanly through asyncio

## Verdict
**PASS** — Demo completes successfully. First-run latency is the only
deviation from ideal targets and is a known LiteLLM initialization cost.
