# Failure Telemetry Report — Phase C

Date: 2026-05-24 07:59 UTC

**Failure telemetry completeness audit results.**

## Summary

- PASS: 5
- FAIL: 0
- CRITICAL: 0

## Individual Results

- [PASS] Telemetry counters populated — counters={"orchestrator.tasks_started_total": 5.0, "model.warm_up_failures_total": 1.0, "event_store.rows_written_total": 37.0, "event_store.write_batches_total": 37.0, "provider.failures_total[failure_class=unexpected:ModuleNotFoundError,provider=ollama/qwen2.5:1.5b-instruct]": 9.0, "provider.attempts_total": 9.0, "provider.retries_total": 9.0, "provider.success_total[provider=mock-byok]": 9.0, "sandbox.success_total[action=read_file]": 1.0, "orchestrator.tasks_completed_total[success=False]": 3.0, "sandbox.failures_total[action=run_terminal]": 1.0, "runtime.failures_total[span=orchestrator.run_task]": 1.0, "orchestrator.failures_total[error_type=SandboxExecutionError]": 1.0, "event_store.read_queries_total": 2.0, "orchestrator.tasks_completed_total[success=True]": 2.0, "sandbox.success_total[action=list_files]": 1.0}
- [PASS] Audit log events recorded — count=12
- [PASS] Sandbox invocations recorded — count=9
- [PASS] Task completions recorded — count=15
- [PASS] Task errors logged to event store — count=3

## Recoverability Classification
- Recoverable failures: Provider timeouts, connection errors, stale sessions
- Non-recoverable: Database page corruption (data loss possible)
- Degraded mode: WAL corruption with partial data access