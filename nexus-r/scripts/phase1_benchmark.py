from __future__ import annotations
# ruff: noqa: E402

import asyncio
import json
import os
import statistics
import subprocess
import sys
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nexus_r.config import NEXUSConfig
from nexus_r.events import Event
from modules.orchestrator.src.orchestrator import MainOrchestrator


def summarize_latencies(latencies: list[float]) -> dict[str, float]:
    ordered = sorted(latencies)
    index_95 = max(0, min(len(ordered) - 1, int(len(ordered) * 0.95) - 1))
    return {
        "min_ms": round(ordered[0], 2),
        "p50_ms": round(statistics.median(ordered), 2),
        "p95_ms": round(ordered[index_95], 2),
        "max_ms": round(ordered[-1], 2),
        "avg_ms": round(sum(ordered) / len(ordered), 2),
    }


async def benchmark_startup(workspace: Path) -> dict[str, float]:
    config = NEXUSConfig.default(workspace)
    orchestrator = MainOrchestrator(config)
    try:
        started = time.perf_counter()
        await orchestrator.initialize()
        startup_ms = (time.perf_counter() - started) * 1000
        return {"startup_ms": round(startup_ms, 2)}
    finally:
        await orchestrator.close()


async def benchmark_event_store(workspace: Path) -> dict[str, float | int]:
    config = NEXUSConfig.default(workspace)
    orchestrator = MainOrchestrator(config)
    await orchestrator.initialize()
    try:
        sequential_events = [
            Event(event_type="benchmark_event_single", data={"index": i, "payload": "x" * 32})
            for i in range(10000)
        ]
        started = time.perf_counter()
        for event in sequential_events:
            await orchestrator.event_store.append(event)
        sequential_ms = (time.perf_counter() - started) * 1000

        batch_events = [
            Event(event_type="benchmark_event_batch", data={"index": i, "payload": "y" * 32})
            for i in range(10000)
        ]
        started = time.perf_counter()
        await orchestrator.event_store.append_many(batch_events)
        batch_ms = (time.perf_counter() - started) * 1000

        parent_id = None
        for i in range(100):
            parent_id = await orchestrator.event_store.append(
                Event(event_type="chain_event", data={"index": i}, parent_event_id=parent_id)
            )
        started = time.perf_counter()
        chain = await orchestrator.event_store.get_chain(parent_id)
        chain_ms = (time.perf_counter() - started) * 1000

        telemetry = orchestrator.get_telemetry_snapshot()
        return {
            "sqlite_append_10000_ms": round(sequential_ms, 2),
            "sqlite_append_avg_ms": round(sequential_ms / 10000.0, 4),
            "sqlite_batch_append_10000_ms": round(batch_ms, 2),
            "sqlite_batch_append_avg_ms": round(batch_ms / 10000.0, 4),
            "event_chain_100_ms": round(chain_ms, 2),
            "event_chain_length": len(chain),
            "write_batches_total": int(telemetry["counters"].get("event_store.write_batches_total", 0)),
            "rows_written_total": int(telemetry["counters"].get("event_store.rows_written_total", 0)),
        }
    finally:
        await orchestrator.close()


async def benchmark_concurrency(workspace: Path, task_count: int) -> dict[str, object]:
    config = NEXUSConfig.default(workspace)
    orchestrator = MainOrchestrator(config)
    try:
        latencies: list[float] = []

        async def run_one(index: int) -> dict[str, object]:
            prompt = f"hello benchmark task {index}"
            started = time.perf_counter()
            result = await orchestrator.run_task(prompt)
            latencies.append((time.perf_counter() - started) * 1000)
            return result

        tracemalloc.start()
        started = time.perf_counter()
        results = await asyncio.gather(*(run_one(i) for i in range(task_count)), return_exceptions=True)
        total_ms = (time.perf_counter() - started) * 1000
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        success_count = 0
        failure_count = 0
        mock_count = 0
        exception_count = 0
        for item in results:
            if isinstance(item, Exception):
                exception_count += 1
                continue
            if item.get("success"):
                success_count += 1
            else:
                failure_count += 1
            if str(item.get("routing_model", "")).startswith("mock"):
                mock_count += 1

        telemetry = orchestrator.get_telemetry_snapshot()
        return {
            "task_count": task_count,
            "total_ms": round(total_ms, 2),
            "latency": summarize_latencies(latencies),
            "success_count": success_count,
            "failure_count": failure_count,
            "exception_count": exception_count,
            "mock_routing_count": mock_count,
            "memory_current_kb": round(current / 1024, 2),
            "memory_peak_kb": round(peak / 1024, 2),
            "provider_queue_depth": telemetry["gauges"].get("provider.queue_depth", 0.0),
            "provider_active_requests": telemetry["gauges"].get("provider.active_requests", 0.0),
            "provider_retries_total": telemetry["counters"].get("provider.retries_total", 0.0),
            "event_rows_written_total": telemetry["counters"].get("event_store.rows_written_total", 0.0),
        }
    finally:
        await orchestrator.close()


def benchmark_cli(workspace: Path) -> dict[str, float | int]:
    python = Path(sys.executable)
    env = os.environ.copy()
    env.update({"PYTHONPATH": os.pathsep.join([str(ROOT / "foundation"), str(ROOT)])})

    started = time.perf_counter()
    config_run = subprocess.run(
        [str(python), "-m", "modules.cli.src.main", "config", "--workspace", str(workspace)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    config_ms = (time.perf_counter() - started) * 1000

    started = time.perf_counter()
    hello_run = subprocess.run(
        [str(python), "-m", "modules.cli.src.main", "run", "hello", "--workspace", str(workspace)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    run_ms = (time.perf_counter() - started) * 1000

    return {
        "cli_config_ms": round(config_ms, 2),
        "cli_run_ms": round(run_ms, 2),
        "cli_config_exit": config_run.returncode,
        "cli_run_exit": hello_run.returncode,
    }


async def main() -> None:
    workspace = ROOT / ".benchmark-workspace"
    workspace.mkdir(exist_ok=True)
    (workspace / "src").mkdir(exist_ok=True)
    (workspace / "src" / "sample.py").write_text("print('bench')\n", encoding="utf-8")
    results = {
        "startup": await benchmark_startup(workspace),
        "event_store": await benchmark_event_store(workspace),
        "concurrency_20": await benchmark_concurrency(workspace, 20),
        "concurrency_50": await benchmark_concurrency(workspace, 50),
        "concurrency_100": await benchmark_concurrency(workspace, 100),
        "cli": benchmark_cli(workspace),
    }
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
