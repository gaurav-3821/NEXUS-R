"""
Kill criterion test for ETD cost reduction.

Runs the same task 5 times through MainOrchestrator and measures
cost and latency reduction from ETD caching.

Expected: cost reduction >= 40%, latency reduction >= 40%,
          runs 2-5 served from ETD cache.
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nexus_r.config import NEXUSConfig
from modules.orchestrator.src.orchestrator import MainOrchestrator


TASK = "list all python files"
NUM_RUNS = 5
MIN_COST_REDUCTION = 0.40
MIN_LATENCY_REDUCTION = 0.40


async def main() -> int:
    workspace = Path.cwd()
    config = NEXUSConfig.default(workspace)
    orch = MainOrchestrator(config)

    results: list[dict] = []
    cost_before = 0.0

    try:
        for i in range(NUM_RUNS):
            start = time.monotonic()
            payload = await orch.run_task(TASK)
            elapsed_ms = (time.monotonic() - start) * 1000

            cost_after = await orch.get_cost_summary()
            total_cost = cost_after.get("totals", {}).get("total_cost", 0.0)
            run_cost = total_cost - cost_before
            cost_before = total_cost

            route = "etd" if payload.get("routing_model") is None else str(payload.get("routing_model", "unknown"))
            source = "cached" if route == "etd" else "model"

            results.append({
                "execution": i + 1,
                "route": route,
                "source": source,
                "cost": round(run_cost, 6),
                "latency_ms": round(elapsed_ms, 2),
                "success": payload.get("success", False),
            })
    finally:
        await orch.close()

    model_runs = [r for r in results if r["source"] == "model"]
    cache_runs = [r for r in results if r["source"] == "cached"]

    avg_model_cost = sum(r["cost"] for r in model_runs) / len(model_runs) if model_runs else 0.0
    avg_model_latency = sum(r["latency_ms"] for r in model_runs) / len(model_runs) if model_runs else 0.0
    avg_cache_cost = sum(r["cost"] for r in cache_runs) / len(cache_runs) if cache_runs else 0.0
    avg_cache_latency = sum(r["latency_ms"] for r in cache_runs) / len(cache_runs) if cache_runs else 0.0

    cost_reduction = (avg_model_cost - avg_cache_cost) / avg_model_cost * 100 if avg_model_cost > 0 else 0.0
    latency_reduction = (avg_model_latency - avg_cache_latency) / avg_model_latency * 100 if avg_model_latency > 0 else 0.0

    print()
    print("=" * 70)
    print(f"  ETD Cost Reduction — Kill Criterion Test")
    print(f"  Task: {TASK!r}")
    print("=" * 70)
    print(f"  {'Exec':>5} | {'Route':>10} | {'Source':>8} | {'Cost':>8} | {'Latency(ms)':>10} | {'Success':>8}")
    print(f"  {'-' * 5} | {'-' * 10} | {'-' * 8} | {'-' * 8} | {'-' * 10} | {'-' * 8}")
    for r in results:
        print(f"  {r['execution']:>5} | {r['route']:>10} | {r['source']:>8} | ${r['cost']:<6.4f} | {r['latency_ms']:>8.2f}ms | {str(r['success']):>8}")
    print("=" * 70)
    print(f"  Model avg cost:     ${avg_model_cost:.6f}")
    print(f"  Cache avg cost:     ${avg_cache_cost:.6f}")
    print(f"  Cost reduction:     {cost_reduction:.1f}%  (target: >= {MIN_COST_REDUCTION * 100:.0f}%)")
    print()
    print(f"  Model avg latency:  {avg_model_latency:.2f}ms")
    print(f"  Cache avg latency:  {avg_cache_latency:.2f}ms")
    print(f"  Latency reduction:  {latency_reduction:.1f}%  (target: >= {MIN_LATENCY_REDUCTION * 100:.0f}%)")
    print("=" * 70)

    passed = True
    if not results[0]["success"]:
        print(f"\n  FAIL: First execution did not succeed")
        passed = False
    if results[0]["source"] == "cached":
        print(f"\n  FAIL: First execution should use model, not cache")
        passed = False
    for i in range(1, NUM_RUNS):
        if results[i]["source"] != "cached":
            print(f"\n  FAIL: Execution {i + 1} should use ETD cache (got {results[i]['source']})")
            passed = False
    if avg_model_cost > 0 and cost_reduction < MIN_COST_REDUCTION * 100:
        print(f"\n  FAIL: Cost reduction {cost_reduction:.1f}% < target {MIN_COST_REDUCTION * 100:.0f}%")
        passed = False
    if latency_reduction < MIN_LATENCY_REDUCTION * 100:
        print(f"\n  FAIL: Latency reduction {latency_reduction:.1f}% < target {MIN_LATENCY_REDUCTION * 100:.0f}%")
        passed = False

    print(f"\n  {'PASS' if passed else 'FAIL'} — Kill criterion {'met' if passed else 'not met'}")
    print("=" * 70)
    print()
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
