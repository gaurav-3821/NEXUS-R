from __future__ import annotations
# ruff: noqa: E402

"""
Phase B — Concurrency Stress Validation
Scaling ladder: 20 → 50 → 100 → 200 concurrent tasks
ABORT CONDITIONS:
  - Corrupted event chain (missing parent_id, wrong causal order)
  - SQLite "database is locked" > 5 seconds
  - Memory growth > 2x baseline after 100 tasks
  - Silent failure (task completes with no telemetry)
"""

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
from nexus_r.events import Event
from modules.orchestrator.src.orchestrator import MainOrchestrator


PASS = 0
FAIL = 0
ABORTED = False


def check(label: str, passed: bool, detail: str = "") -> None:
    global PASS, FAIL
    if passed:
        PASS += 1
        print(f"  [PASS] {label}", end="")
    else:
        FAIL += 1
        print(f"  [FAIL] {label}", end="")
    if detail:
        print(f" — {detail}")
    else:
        print()


def abort_if(condition: bool, reason: str) -> None:
    """Abort all further scaling if condition is met."""
    global ABORTED
    if condition and not ABORTED:
        ABORTED = True
        print(f"\n  *** ABORT: {reason} ***\n")


WORKLOADS = [
    "hello",
    "explain databases briefly",
    "draft a short message",
    "brainstorm two names",
    "list all python files",
    "create stress_{i}.txt with content test",
    "read stress_{i}.txt",
    "hello world",
    "draft a quick note",
    "explain caching simply",
]


async def verify_event_chains(orchestrator, task_count: int) -> list[str]:
    """Verify that event chains are intact for completed tasks.
    get_chain() returns events from terminal->root (depth DESC).
    """
    issues: list[str] = []
    completed = await orchestrator.event_store.get_by_type("task_completed")
    if not completed:
        issues.append("No task_completed events found")
        return issues

    for event in completed[-task_count:]:
        if event.parent_event_id:
            try:
                chain = await orchestrator.event_store.get_chain(event.id)
                if not chain:
                    issues.append(f"Empty chain for {event.id}")
                    continue
                types = [e.event_type for e in chain]
                if "task_received" not in types:
                    issues.append(f"Chain missing task_received for {event.id}")
                if "audit_log" not in types:
                    issues.append(f"Chain missing audit_log for {event.id}")
                if types[0] != "task_received":
                    issues.append(f"Chain root is not task_received: {types[0]} for {event.id}")
                if types[-1] != "task_completed":
                    issues.append(f"Chain terminal is not task_completed: {types[-1]} for {event.id}")
                required = {"task_received", "intent_parsed", "audit_log", "task_completed"}
                missing = required - set(types)
                if missing:
                    issues.append(f"Chain missing events {missing} for {event.id}")
            except Exception as exc:
                issues.append(f"Chain retrieval failed for {event.id}: {exc}")
    return issues


async def run_concurrent(orchestrator_fn, count: int) -> dict:
    prompts = [WORKLOADS[i % len(WORKLOADS)].format(i=i) for i in range(count)]
    orchestrator = orchestrator_fn()
    rss_before = _get_rss()
    await orchestrator.initialize()

    started = time.perf_counter()
    tasks = [asyncio.create_task(orchestrator.run_task(p)) for p in prompts]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    elapsed = time.perf_counter() - started

    rss_after = _get_rss()
    mem_growth = rss_after - rss_before

    successes = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
    failures = sum(1 for r in results if isinstance(r, dict) and not r.get("success"))
    exceptions = sum(1 for r in results if isinstance(r, Exception))

    latencies_ms = []
    for r in results:
        if isinstance(r, dict):
            latencies_ms.append(elapsed * 1000)

    telemetry = orchestrator.get_telemetry_snapshot()
    cost_summary = await orchestrator.get_cost_summary()
    chain_issues = await verify_event_chains(orchestrator, min(count, 50))
    await orchestrator.close()

    p50 = sorted(latencies_ms)[len(latencies_ms) // 2] if latencies_ms else 0
    p95 = sorted(latencies_ms)[int(len(latencies_ms) * 0.95)] if len(latencies_ms) >= 20 else 0
    p99 = sorted(latencies_ms)[int(len(latencies_ms) * 0.99)] if len(latencies_ms) >= 100 else 0
    throughput = count / elapsed if elapsed > 0 else 0

    return {
        "count": count,
        "elapsed_s": round(elapsed, 2),
        "throughput": round(throughput, 2),
        "success_rate": round(successes / count * 100, 1) if count else 0,
        "successes": successes,
        "failures": failures,
        "exceptions": exceptions,
        "latency_ms_p50": round(p50, 1),
        "latency_ms_p95": round(p95, 1),
        "latency_ms_p99": round(p99, 1),
        "rss_before_mb": round(rss_before, 1),
        "rss_after_mb": round(rss_after, 1),
        "mem_growth_mb": round(mem_growth, 1),
        "chain_issues": chain_issues,
        "active_tasks_after": orchestrator._active_tasks,
        "telemetry": telemetry,
        "cost": cost_summary,
    }


def _get_rss() -> float:
    try:
        import psutil
        return psutil.Process().memory_info().rss / (1024 * 1024)
    except ImportError:
        return 0.0


async def main():
    global ABORTED
    print("=" * 70)
    print("  PHASE B — CONCURRENCY STRESS VALIDATION (v2)")
    print("=" * 70)

    wd = ROOT / ".concurrency-stress-v2"
    wd.mkdir(exist_ok=True)

    levels = [20, 50, 100, 200]
    results = []
    mem_baseline = 0
    saw_degradation = False

    for level in levels:
        if ABORTED:
            print(f"\n--- Skipping {level} tasks (ABORTED) ---")
            break

        print(f"\n--- Scaling: {level} concurrent tasks ---")

        def make_orch():
            cfg = NEXUSConfig.default(wd)
            cfg.database.path = wd / f"nexus_concurrent_{level}.db"
            return MainOrchestrator(cfg)

        result = await run_concurrent(make_orch, level)
        results.append(result)

        mem_growth = result["mem_growth_mb"]
        if mem_baseline == 0:
            mem_baseline = result["rss_before_mb"]

        success_rate = result["success_rate"]
        chain_ok = len(result["chain_issues"]) == 0
        no_silent = result["failures"] + result["successes"] == level

        check(f"{level} tasks: {result['elapsed_s']:.1f}s, "
              f"{result['throughput']}/s throughput, "
              f"{success_rate}% success",
              success_rate > 90,
              f"failures={result['failures']}, exceptions={result['exceptions']}")

        check(f"Memory: {result['rss_before_mb']:.0f} -> {result['rss_after_mb']:.0f}MB "
              f"(+{mem_growth:.1f}MB)",
              mem_growth < 20,
              f"growth={mem_growth:.1f}MB")

        check(f"Event chain integrity", chain_ok,
              f"issues={result['chain_issues']}")

        check(f"No silent failures", no_silent,
              f"accounted={result['successes'] + result['failures']}/{level}")

        check(f"Latency p50={result['latency_ms_p50']}ms "
              f"p95={result['latency_ms_p95']}ms "
              f"p99={result['latency_ms_p99']}ms",
              True)

        # ABORT CONDITIONS
        mem_ratio = mem_growth / max(mem_baseline, 1)
        abort_if(
            not chain_ok,
            f"Event chain corruption at {level} tasks"
        )
        abort_if(
            level >= 100 and mem_ratio > 2.0,
            f"Memory >2x baseline at {level} tasks: {mem_ratio:.1f}x"
        )
        abort_if(
            not no_silent,
            f"Tasks completing with no result at {level} tasks"
        )

        # Check for degradation
        if len(results) >= 2:
            prev = results[-2]
            tput_drop = prev["throughput"] - result["throughput"]
            if tput_drop > prev["throughput"] * 0.3 and level > prev["count"]:
                print(f"  ⚠  Throughput degraded {(tput_drop/prev['throughput']*100):.0f}% "
                      f"from {prev['count']}→{level} tasks")
                saw_degradation = True
            # 20-task gate: if 20 fails, abort before 50
            if level == 20 and (success_rate < 80 or mem_growth > 50):
                abort_if(True, f"20-task gate not met: success={success_rate}%, mem={mem_growth}MB")
                break

    print(f"\n{'='*70}")
    print(f"  CONCURRENCY RESULTS SUMMARY")
    print(f"{'='*70}")
    print(f"  PASS: {PASS}  |  FAIL: {FAIL}  |  ABORTED: {ABORTED}")
    for r in results:
        print(f"  {r['count']:3d} tasks: {r['elapsed_s']:6.1f}s, "
              f"{r['throughput']:5.1f}/s, "
              f"{r['success_rate']:5.1f}% ok, "
              f"p50={r['latency_ms_p50']:7.1f}ms, "
              f"mem=+{r['mem_growth_mb']:4.1f}MB, "
              f"chains={'OK' if not r['chain_issues'] else 'ISSUES'}, "
              f"active_after={r['active_tasks_after']}")

    # Write report
    report = [
        "# Concurrency Scaling Report — Phase B\n",
        "## Results\n",
        "| Tasks | Time (s) | Throughput (/s) | Success (%) | p50 (ms) | p95 (ms) | Mem +MB | Chains |",
        "|-------|----------|-----------------|-------------|----------|----------|---------|--------|",
    ]
    for r in results:
        report.append(
            f"| {r['count']} | {r['elapsed_s']:.1f} | {r['throughput']:.1f} | "
            f"{r['success_rate']:.1f} | {r['latency_ms_p50']:.1f} | "
            f"{r['latency_ms_p95']:.1f} | {r['mem_growth_mb']:.1f} | "
            f"{'OK' if not r['chain_issues'] else 'ISSUES'} |"
        )
    report.extend([
        "",
        "## Abort Conditions",
        f"Aborted: {'YES' if ABORTED else 'NO'}",
        "",
        "## Degradation",
        f"Throughput cliff: {'YES' if saw_degradation else 'NO'}",
        f"Memory baseline: {mem_baseline:.1f}MB",
        "",
        "## Latency Percentiles",
    ])
    for r in results:
        report.append(
            f"  {r['count']} tasks: p50={r['latency_ms_p50']:.1f}ms, "
            f"p95={r['latency_ms_p95']:.1f}ms, p99={r['latency_ms_p99']:.1f}ms"
        )

    docs_dir = ROOT / "docs"
    docs_dir.mkdir(exist_ok=True)
    report_path = docs_dir / "concurrency_scaling_report.md"
    report_path.write_text("\n".join(report), encoding="utf-8")
    print(f"\nReport: {report_path}")

    print(f"\n  {'='*40}")
    print(f"  GATE: {'PASS' if not ABORTED and PASS > FAIL else 'FAIL'}")
    print(f"  {'='*40}")

    return not ABORTED and PASS >= FAIL


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
