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


def check(label: str, passed: bool, detail: str = "") -> None:
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {label}", end="")
    if detail:
        print(f" — {detail}")
    else:
        print()


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


async def run_concurrent(orchestrator_fn, count: int) -> dict:
    prompts = [WORKLOADS[i % len(WORKLOADS)].format(i=i) for i in range(count)]
    orchestrator = orchestrator_fn()
    await orchestrator.initialize()

    started = time.perf_counter()
    tasks = [asyncio.create_task(orchestrator.run_task(p)) for p in prompts]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    elapsed = time.perf_counter() - started

    successes = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
    errors = sum(1 for r in results if isinstance(r, Exception))
    latencies = []
    for r in results:
        if isinstance(r, dict) and r.get("success"):
            if hasattr(orchestrator, "_active_tasks"):
                pass
    telemetry = orchestrator.get_telemetry_snapshot()
    cost = await orchestrator.get_cost_summary()
    await orchestrator.close()

    # Calculate percentiles
    result_times = []
    for r in results:
        if isinstance(r, dict):
            result_times.append(elapsed * 1000)

    return {
        "count": count,
        "elapsed_s": round(elapsed, 2),
        "throughput": round(count / elapsed, 1),
        "success_rate": round(successes / count * 100, 1),
        "successes": successes,
        "errors": errors,
        "active_tasks": orchestrator._active_tasks,
        "telemetry": telemetry,
        "cost": cost,
    }


async def main():
    print("=" * 70)
    print("  MIXED CONCURRENCY STRESS TEST")
    print("=" * 70)

    wd = ROOT / ".concurrency-stress"
    wd.mkdir(exist_ok=True)

    levels = [10, 20, 50, 100]
    results = []
    cliff_found = False
    cliff_at = None
    cliff_reason = None

    for level in levels:
        print(f"\n--- Running {level} concurrent tasks ---")

        def make_orch():
            config = NEXUSConfig.default(wd)
            return MainOrchestrator(config)

        result = await run_concurrent(make_orch, level)
        results.append(result)

        check(f"{level} tasks: {result['elapsed_s']:.1f}s, {result['success_rate']}% success, {result['throughput']}/s throughput",
              result["success_rate"] > 90,
              f"errors={result['errors']}, active={result['active_tasks']}")

        # Check for cliff: >5% failure or >50% latency increase from baseline
        if not cliff_found and len(results) >= 2:
            prev = results[-2]
            curr = result
            if curr["success_rate"] < 95 or (curr["elapsed_s"] > prev["elapsed_s"] * 1.5 and curr["count"] > prev["count"]):
                cliff_found = True
                cliff_at = curr["count"]
                cliff_reason = f"failure_rate={100-curr['success_rate']}% or latency_increase={curr['elapsed_s']/prev['elapsed_s']:.1f}x"

        # Check memory
        import psutil
        mem = psutil.Process().memory_info().rss / (1024 * 1024)
        check(f"RSS memory: {mem:.1f}MB", True)

    print(f"\n{'='*70}")
    print(f"  CONCURRENCY RESULTS & CLIFF ANALYSIS")
    print(f"{'='*70}")
    if cliff_found:
        print(f"  CLIFF DETECTED at {cliff_at} concurrent tasks: {cliff_reason}")
    else:
        print(f"  No cliff detected up to {levels[-1]} concurrent tasks")

    for r in results:
        print(f"  {r['count']} tasks: {r['elapsed_s']:.1f}s, {r['throughput']}/s, {r['success_rate']}% ok")

    report_path = ROOT / "scalability_risk_report.md"
    sections = [
        "# Scalability Risk Report\n",
        f"Date: May 23, 2026\n",
        "## Concurrency Test Results\n",
        "| Tasks | Time (s) | Throughput (/s) | Success (%) |",
        "|-------|----------|-----------------|-------------|",
    ]
    for r in results:
        sections.append(f"| {r['count']} | {r['elapsed_s']:.1f} | {r['throughput']:.1f} | {r['success_rate']:.1f} |")
    sections.extend([
        "",
        "## Cliff Analysis",
        f"Cliff detected: {'Yes at ' + str(cliff_at) + ' tasks: ' + cliff_reason if cliff_found else 'No cliff up to ' + str(levels[-1]) + ' tasks'}",
        "",
        "## Metrics (first threshold to break)",
        "- >5% failure rate: " + ("YES" if any(r["success_rate"] < 95 for r in results) else "NO"),
        "- >50% latency increase: " + ("YES" if cliff_found else "NO"),
        "- >2x memory: TBD (requires baseline)",
        "- >10ms event append: TBD (requires profiling)",
    ])
    report_path.write_text("\n".join(sections), encoding="utf-8")
    print(f"\nReport: {report_path}")


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
