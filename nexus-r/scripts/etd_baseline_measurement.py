from __future__ import annotations

"""
ETD Latency Baseline Measurement — Phase D, Task 1.

Measures first-run (cold cache) vs second-run (warm cache) latency
across 10 independent trials. Reports actual reduction % per trial
and overall statistics.

Usage: python scripts/etd_baseline_measurement.py
Output: /tmp/etd_latency_baseline.json  (or C:\tmp\ on Windows)
"""

import asyncio
import json
import math
import os
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nexus_r.config import NEXUSConfig
from modules.orchestrator.src.orchestrator import MainOrchestrator


TASK = "list all python files"
NUM_TRIALS = 10
BASELINE_PATH = Path(os.environ.get("TMPDIR", "/tmp" if sys.platform != "win32" else "C:\\tmp")) / "etd_latency_baseline.json"


def t_student_paired(diffs: list[float]) -> float:
    n = len(diffs)
    if n < 2:
        return 1.0
    mean = sum(diffs) / n
    variance = sum((d - mean) ** 2 for d in diffs) / (n - 1)
    if variance == 0:
        return 0.0
    t = mean / math.sqrt(variance / n)
    # Approximate p-value from t-distribution (one-tailed)
    df = n - 1
    p = 0.5 * (1 + math.erf(t / math.sqrt(2)))
    return 1.0 - p


async def measure_one_trial(workspace: Path) -> dict:
    """Run one first+second measurement pair; return latencies and reduction."""
    config = NEXUSConfig.default(workspace)
    orch = MainOrchestrator(config)

    try:
        # First run (cold cache)
        start1 = time.monotonic()
        r1 = await orch.run_task(TASK)
        t1 = (time.monotonic() - start1) * 1000

        # Second run (warm cache — ETD should have learned)
        start2 = time.monotonic()
        r2 = await orch.run_task(TASK)
        t2 = (time.monotonic() - start2) * 1000

        reduction = ((t1 - t2) / t1 * 100) if t1 > 0 else 0.0
        return {
            "trial": 0,
            "first_latency_ms": round(t1, 2),
            "second_latency_ms": round(t2, 2),
            "reduction_pct": round(reduction, 2),
            "first_success": r1.get("success", False),
            "second_success": r2.get("success", False),
            "first_source": "model" if r1.get("routing_model") else "etd",
            "second_source": "model" if r2.get("routing_model") else "etd",
        }
    finally:
        await orch.close()


async def main() -> int:
    # Ensure parent dir exists
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)

    trials: list[dict] = []
    for i in range(NUM_TRIALS):
        wd = ROOT / ".etd-baseline-tmp" / str(i)
        wd.mkdir(parents=True, exist_ok=True)
        (wd / "src").mkdir(exist_ok=True)
        (wd / "src" / "dummy.py").write_text("# placeholder\n")
        try:
            result = await measure_one_trial(wd)
        except Exception as exc:
            print(f"  Trial {i+1:>2}: ERROR — {exc}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            continue
        result["trial"] = i + 1
        trials.append(result)
        marker = "OK" if result["reduction_pct"] > 0 and result["first_success"] and result["second_success"] else "WARN"
        print(
            f"  Trial {i+1:>2} [{marker}]: "
            f"first={result['first_latency_ms']:.1f}ms ({result['first_source']}), "
            f"second={result['second_latency_ms']:.1f}ms ({result['second_source']}), "
            f"reduction={result['reduction_pct']:.1f}%"
        )

    if not trials:
        print("\n  FATAL: No trials succeeded")
        return 1

    first_latencies = [t["first_latency_ms"] for t in trials]
    second_latencies = [t["second_latency_ms"] for t in trials]
    reductions = [t["reduction_pct"] for t in trials]

    mean_first = sum(first_latencies) / len(first_latencies)
    mean_second = sum(second_latencies) / len(second_latencies)
    mean_reduction = sum(reductions) / len(reductions)
    var_first = sum((x - mean_first) ** 2 for x in first_latencies) / len(first_latencies)
    var_second = sum((x - mean_second) ** 2 for x in second_latencies) / len(second_latencies)
    cv_first = math.sqrt(var_first) / mean_first if mean_first > 0 else 0.0
    cv_second = math.sqrt(var_second) / mean_second if mean_second > 0 else 0.0

    p_value = t_student_paired(
        [f - s for f, s in zip(first_latencies, second_latencies)]
    )

    baseline = {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "num_trials": len(trials),
            "task": TASK,
            "platform": sys.platform,
        },
        "per_trial": trials,
        "statistics": {
            "mean_first_latency_ms": round(mean_first, 2),
            "mean_second_latency_ms": round(mean_second, 2),
            "mean_reduction_pct": round(mean_reduction, 2),
            "first_latency_variance_ms2": round(var_first, 4),
            "second_latency_variance_ms2": round(var_second, 4),
            "first_cv": round(cv_first, 4),
            "second_cv": round(cv_second, 4),
            "paired_t_p_value": round(p_value, 6),
            "significant": p_value < 0.05,
            "all_trials_improved": all(r > 0 for r in reductions),
            "all_first_successful": all(t["first_success"] for t in trials),
            "all_second_successful": all(t["second_success"] for t in trials),
        },
    }

    BASELINE_PATH.write_text(json.dumps(baseline, indent=2), encoding="utf-8")

    print()
    print("=" * 70)
    print("  ETD BASELINE MEASUREMENT RESULTS")
    print("=" * 70)
    print(f"  Trials completed:         {len(trials)} / {NUM_TRIALS}")
    print(f"  Mean first-run latency:   {mean_first:.2f} ms")
    print(f"  Mean second-run latency:  {mean_second:.2f} ms")
    print(f"  Mean reduction:           {mean_reduction:.2f}%")
    print(f"  First-run CV:             {cv_first:.4f}")
    print(f"  Second-run CV:            {cv_second:.4f}")
    print(f"  Paired t-test p-value:    {p_value:.6f}")
    print(f"  All trials improved:      {all(r > 0 for r in reductions)}")
    print(f"  All first succeeded:      {all(t['first_success'] for t in trials)}")
    print(f"  All second succeeded:     {all(t['second_success'] for t in trials)}")
    print(f"  Saved to:                 {BASELINE_PATH}")
    print("=" * 70)
    print()

    below_40 = sum(1 for r in reductions if r < 40.0)
    print(f"  Trials below 40% target:  {below_40} / {len(trials)}")
    if below_40 > 0:
        print(f"  ACTION NEEDED: Optimize ETD to push all trials >= 40% reduction")

    return 0 if all(r > 0 for r in reductions) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
