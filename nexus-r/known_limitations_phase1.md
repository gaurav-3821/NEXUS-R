# Known Limitations

## Functional Limitations

1. BYOK execution is still unverified because no real provider API key was available on May 23, 2026.
2. The local model path is real, but the current 2-tier fallback proof stops at `local -> mock` in practice on this machine.
3. The classifier is still heuristic. It is better than before, but it is not robust against varied natural-language phrasing.
4. Search and file operations are Phase 1-simple and not policy-rich.

## Runtime Limitations

1. Cold local-model latency is high. The first real `hello` request took seconds, not milliseconds.
   A fire-and-forget model warm-up runs during CLI startup to preload LiteLLM,
   reducing the first visible task latency.
2. Concurrency remains stable but slow because Ollama inference is the dominant bottleneck.
3. EventStore batch performance is strong, but strict synchronous single-append latency still misses the `<1 ms` target.
4. CLI responsiveness is acceptable for admin commands, but cold `run` latency is dominated by model load.
5. Memory grows ~3× during heavy use (61 MB startup → ~200 MB steady state) due to
   SQLite WAL cache (`PRAGMA cache_size=-64000` = ~64 MB) and telemetry buffer accumulation.
   Growth plateaus at ~200 MB. This is a bounded cache, not an unbounded leak.
   Configurable via `NEXUSConfig.DatabaseSettings.sqlite_cache_size_mb` (default 50) — fix scheduled for Phase 2.

## Security Limitations

1. Identity encryption is still development-grade only.
2. Corrupted identity ciphertext still raises `InvalidToken` instead of a controlled recovery flow.
3. Session state files exist in the repo from prior work and remain out of Phase 1 scope.
4. Prompt injection is reduced by architecture and task gating, not solved.

## Validation Limitations

1. Real BYOK fallback was not proven.
2. Fake-server failure tests fail closed, but they currently collapse to a generic `No providers or mock fallbacks are available` surface instead of rich provider-specific errors.
3. Mid-inference persistence was partially observed through task state and post-completion provider events, but the exact mid-flight provider-invocation visibility is still timing-sensitive.
