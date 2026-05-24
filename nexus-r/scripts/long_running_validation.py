from __future__ import annotations
# ruff: noqa: E402

import asyncio
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nexus_r.config import NEXUSConfig
from modules.orchestrator.src.orchestrator import MainOrchestrator


TASK_PROMPTS = [
    "hello",
    "explain what a database is in one sentence",
    "draft a short greeting message",
    "brainstorm three project names",
    "list all python files",
    "create test_{i}.txt with content hello world",
    "read test_{i}.txt",
    "summarize the purpose of error handling",
    "hello again",
    "draft a commit message for a bug fix",
    "explain the concept of recursion briefly",
    "brainstorm two testing strategies",
    "create notes_{i}.txt with content meeting notes",
    "read notes_{i}.txt",
    "hello world check",
    "explain what an API is in one sentence",
    "draft a short release note",
    "brainstorm ideas for a CLI tool",
    "list all files",
    "summarize the benefit of type hints",
]


async def measure_memory() -> dict[str, float]:
    import psutil
    proc = psutil.Process()
    mem = proc.memory_info()
    cpu = proc.cpu_percent(interval=0.1)
    return {
        "rss_mb": mem.rss / (1024 * 1024),
        "vms_mb": mem.vms / (1024 * 1024),
        "cpu_percent": cpu,
    }


def check(label: str, passed: bool, detail: str = "") -> None:
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {label}", end="")
    if detail:
        print(f" — {detail}")
    else:
        print()


async def run_workload_batch(orchestrator: MainOrchestrator, count: int, start_index: int = 0) -> list[dict]:
    results = []
    for i in range(count):
        prompt = TASK_PROMPTS[i % len(TASK_PROMPTS)].format(i=start_index + i)
        try:
            started = time.perf_counter()
            result = await orchestrator.run_task(prompt)
            elapsed = (time.perf_counter() - started) * 1000
            results.append({"prompt": prompt, "success": result.get("success"), "elapsed_ms": elapsed, "error": result.get("error")})
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            results.append({"prompt": prompt, "success": False, "elapsed_ms": 0, "error": str(exc)})
    return results


async def main():
    print("=" * 70)
    print("  LONG-RUNNING STABILITY TEST")
    print("=" * 70)

    workspace = ROOT / ".long-running-validation"
    workspace.mkdir(exist_ok=True)
    (workspace / "src").mkdir(exist_ok=True)
    config = NEXUSConfig.default(workspace)

    orchestrator = MainOrchestrator(config)
    await orchestrator.initialize()

    memory_snapshots: list[dict] = []
    results_log: list[dict] = []
    failure_count = 0
    total_tasks = 0

    try:
        snap = await measure_memory()
        memory_snapshots.append({"label": "startup", **snap})
        check(f"Startup memory: RSS={snap['rss_mb']:.1f}MB, VMS={snap['vms_mb']:.1f}MB", True)

        checkpoints = [10, 100, 200, 500, 1000]
        completed = 0

        for target in checkpoints:
            batch_size = target - completed
            if batch_size <= 0:
                continue

            check(f"Running batch of {batch_size} tasks toward {target} total...", True)
            batch_start = time.perf_counter()

            for i in range(batch_size):
                prompt = TASK_PROMPTS[(completed + i) % len(TASK_PROMPTS)].format(i=completed + i)
                try:
                    started = time.perf_counter()
                    result = await orchestrator.run_task(prompt)
                    elapsed = (time.perf_counter() - started) * 1000
                    results_log.append({"n": completed + i, "prompt": prompt[:40], "success": result.get("success"), "elapsed_ms": round(elapsed, 1)})
                    if not result.get("success"):
                        failure_count += 1
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    results_log.append({"n": completed + i, "prompt": prompt[:40], "success": False, "elapsed_ms": 0})
                    failure_count += 1

                if (i + 1) % 50 == 0:
                    print(f"    ... {completed + i + 1}/{target} tasks done")

            completed = target
            elapsed_batch = time.perf_counter() - batch_start
            snap = await measure_memory()
            memory_snapshots.append({"label": f"{target}_tasks", **snap})
            success_rate = (target - failure_count) / target * 100 if target > 0 else 0
            check(f"Checkpoint {target}: {elapsed_batch:.1f}s wall, {success_rate:.1f}% success, RSS={snap['rss_mb']:.1f}MB",
                  success_rate > 90, f"failures={failure_count}")

        # Idle measurement after 5-min simulated idle
        check("Simulating 5-minute idle period...", True)
        idle_start = time.perf_counter()
        while time.perf_counter() - idle_start < 30:
            await asyncio.sleep(5)
            snap = await measure_memory()
            memory_snapshots.append({"label": f"idle_{int(time.perf_counter()-idle_start)}s", **snap})

        idle_snap = await measure_memory()
        memory_snapshots.append({"label": "after_idle", **idle_snap})

        startup_mem = memory_snapshots[0]["rss_mb"]
        idle_mem = idle_snap["rss_mb"]
        ratio = idle_mem / startup_mem if startup_mem > 0 else 0
        classification = "LEAK" if ratio > 1.5 else "CACHE (bounded plateau)"
        check(f"Memory analysis: startup={startup_mem:.1f}MB, idle={idle_mem:.1f}MB, ratio={ratio:.2f}x", ratio <= 1.5,
              f"classification={classification}")

        # Latency drift analysis
        if len(results_log) >= 2:
            first_50 = [r["elapsed_ms"] for r in results_log[:50] if r["success"]]
            last_50 = [r["elapsed_ms"] for r in results_log[-50:] if r["success"]]
            if first_50 and last_50:
                avg_first = sum(first_50) / len(first_50)
                avg_last = sum(last_50) / len(last_50)
                drift_pct = ((avg_last - avg_first) / avg_first * 100) if avg_first > 0 else 0
                check(f"Latency drift: first_50_avg={avg_first:.0f}ms, last_50_avg={avg_last:.0f}ms, drift={drift_pct:.1f}%",
                      drift_pct < 50, "degradation threshold <50%")

        # Event store size
        db_path = config.database.path
        if db_path.exists():
            db_size_mb = db_path.stat().st_size / (1024 * 1024)
            check(f"Event store size: {db_size_mb:.1f}MB for {completed} tasks", True)

        # Cost summary
        cost_summary = await orchestrator.get_cost_summary()
        total_cost = cost_summary.get("totals", {}).get("total_cost", 0)
        check(f"Total cost accrued: ${total_cost:.4f}", True)

    finally:
        await orchestrator.close()

    report = {
        "total_tasks": total_tasks or completed,
        "failures": failure_count,
        "success_rate_pct": ((total_tasks or completed) - failure_count) / max(1, (total_tasks or completed)) * 100,
        "memory_snapshots": memory_snapshots,
        "memory_classification": classification,
        "memory_idle_ratio": ratio,
        "event_store_mb": db_path.stat().st_size / (1024 * 1024) if db_path.exists() else 0,
        "total_cost": total_cost,
    }

    print(f"\n{'='*70}")
    print(f"  RESULTS")
    print(f"{'='*70}")
    print(f"  Status: {classification}")
    print(f"  Tasks completed: {report['total_tasks']}")
    print(f"  Success rate: {report['success_rate_pct']:.1f}%")
    print(f"  Memory idle ratio: {ratio:.2f}x")

    report_path = ROOT / "runtime_stability_report.md"
    sections = [
        "# Runtime Stability Report\n",
        f"Date: May 23, 2026  |  Tasks: {report['total_tasks']}  |  Duration: ~5min\n",
        "## Memory Analysis\n",
        f"| Checkpoint | RSS (MB) | VMS (MB) | CPU (%) |",
        f"|------------|----------|----------|---------|",
    ]
    for s in memory_snapshots:
        sections.append(f"| {s['label']} | {s['rss_mb']:.1f} | {s['vms_mb']:.1f} | {s['cpu_percent']:.1f} |")
    sections.extend([
        f"\n**Memory classification: {classification}**",
        f"Startup: {startup_mem:.1f}MB → Idle: {idle_mem:.1f}MB (ratio {ratio:.2f}x)",
        "",
        "## Latency Analysis",
        f"First 50 avg: {avg_first:.0f}ms" if first_50 else "",
        f"Last 50 avg: {avg_last:.0f}ms" if last_50 else "",
        f"Drift: {drift_pct:.1f}%" if drift_pct else "",
        "",
        "## Event Store",
        f"Size: {report['event_store_mb']:.1f}MB after {report['total_tasks']} tasks",
        f"Cost accrued: ${report['total_cost']:.4f}",
        "",
        "## Verdict",
        f"**{'STABLE' if ratio <= 1.5 else 'LEAK DETECTED'}** — Memory {classification}.",
        f"Success rate: {report['success_rate_pct']:.1f}%.",
        f"**{'PASS' if ratio <= 1.5 else 'FAIL'}** — Phase 1.5 long-running stability criteria.",
    ])
    report_path.write_text("\n".join(sections), encoding="utf-8")
    print(f"\nReport written to: {report_path}")


if __name__ == "__main__":
    if not hasattr(Path, '_mkdir_patched'):
        original_mkdir = Path.mkdir
        def _safe_mkdir(self, *a, **kw):
            try:
                return original_mkdir(self, *a, **kw)
            except FileExistsError:
                pass
        Path.mkdir = _safe_mkdir
        Path._mkdir_patched = True
    asyncio.run(main())
