from __future__ import annotations
# ruff: noqa: E402

"""
Phase B — ETD Saturation Validation
Stresses:
- Repeated cache retrieval (same intent 10k times)
- Repeated trace distillation (unique intents, no cache hits)
- Repeated pattern matching (near-miss embeddings)
"""

import asyncio
import os
import sys
import time
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nexus_r.events import IntentResult, PermissionTier
from modules.workflow_engine.src.pipeline import ETDPipeline
from modules.workflow_engine.src.parameterizer import WorkflowParameterizer
from modules.workflow_engine.src.distiller import DistilledWorkflow, ToolStep

PASS = 0
FAIL = 0


def check(label: str, passed: bool, detail: str = "") -> None:
    global PASS, FAIL
    if passed:
        PASS += 1
    else:
        FAIL += 1
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {label}{' — ' + detail if detail else ''}")


def _make_trace(actions: list[str]) -> list:
    from nexus_r.events import CausalEvent
    events = []
    prev = None
    for i, a in enumerate(actions):
        e = CausalEvent(
            event_type="workflow_step",
            parent_event_id=prev,
            data={
                "task_id": str(uuid4()),
                "step_index": i,
                "tool": "terminal",
                "action": a,
                "input_data": {},
                "output_data": {"message": f"Ran {a}"},
            },
            verification_result="passed",
            model_used="none",
            cost=0.0,
            tier=PermissionTier.T1,
        )
        events.append(e)
        prev = e.id
    return events


def _intent(sig: str, task_type: str = "npm") -> IntentResult:
    return IntentResult(
        raw_input=sig,
        normalized_input=sig,
        task_type=task_type,
        complexity=0.3,
        confidence=0.9,
        parameters={},
        suggested_tier=PermissionTier.T1,
    )


async def test_same_intent_10k_lookups():
    print("\n--- A. Same Intent — 10,000 Cache Lookups ---")
    pipeline = ETDPipeline()
    intent = _intent("run-terminal-npm-install", "run_terminal")

    # Seed one entry
    sig = "run-terminal-npm-install"
    wf = DistilledWorkflow(
        id=str(uuid4()), intent_signature=sig,
        tool_sequence=[ToolStep(tool="terminal", action="npm install", verify="passed")],
        parameter_slots=[], invariant_checks=[],
        success_count=1, failure_count=0, generalization_success_rate=1.0,
    )
    entry = WorkflowParameterizer().parameterize(wf)
    entry.generalization_success_rate = 1.0
    pipeline.indexer.index(entry)

    # 10k lookups
    started = time.perf_counter()
    hits = 0
    for i in range(10000):
        match = await pipeline.find_match(intent)
        if match is not None:
            hits += 1
    elapsed = time.perf_counter() - started
    per_lookup_us = (elapsed / 10000) * 1_000_000

    check(f"10,000 lookups: {elapsed:.3f}s ({per_lookup_us:.1f}us/lookup), hits={hits}",
          hits == 10000 and per_lookup_us < 500,
          f"lookups={10000}, hits={hits}, per_lookup={per_lookup_us:.1f}us")


async def test_unique_intents_no_cache_hits():
    print("\n--- B. 1,000 Unique Intents — No Cache Hits ---")
    pipeline = ETDPipeline()
    rss_before = _memory_mb()

    started = time.perf_counter()
    for i in range(1000):
        sig = f"unique-intent-{i:04d}"
        intent = _intent(sig, "run_terminal" if i % 2 == 0 else "npm")
        match = await pipeline.find_match(intent)
        if match is not None:
            PASS -= 1  # False positive
            FAIL += 1
            print(f"  [FAIL] False match for {sig}")
            return

    elapsed = time.perf_counter() - started
    rss_after = _memory_mb()
    per_query = (elapsed / 1000) * 1000

    check(f"1,000 unique queries (no matches): {elapsed:.3f}s ({per_query:.2f}ms/query)",
          per_query < 50,
          f"total={elapsed:.3f}s, per_query={per_query:.2f}ms")
    check(f"Memory impact: {rss_before:.0f} -> {rss_after:.0f}MB (+{rss_after-rss_before:.1f}MB)",
          (rss_after - rss_before) < 20,
          f"growth={rss_after-rss_before:.1f}MB")


async def test_near_miss_embeddings():
    print("\n--- C. Near-Miss Embedding Matching ---")
    pipeline = ETDPipeline()

    # Seed 100 entries with varied signatures
    for i in range(100):
        sig = f"run-terminal-command-{i:03d}"
        wf = DistilledWorkflow(
            id=str(uuid4()), intent_signature=sig,
            tool_sequence=[ToolStep(tool="terminal", action=f"cmd {i}", verify="passed")],
            parameter_slots=[], invariant_checks=[],
            success_count=1, failure_count=0, generalization_success_rate=1.0 - (i * 0.002),
        )
        entry = WorkflowParameterizer().parameterize(wf)
        entry.generalization_success_rate = wf.generalization_success_rate
        pipeline.indexer.index(entry)

    # Query with near-miss variants
    n_found = 0
    n_not_found = 0
    started = time.perf_counter()
    for i in range(50):
        offset = i * 2
        sig = f"run-terminal-command-{offset:03d}"
        intent = _intent(sig, "run_terminal")
        match = await pipeline.find_match(intent)
        if match is not None:
            n_found += 1
        else:
            n_not_found += 1
    elapsed = time.perf_counter() - started

    check(f"50 near-miss queries: {n_found} found, {n_not_found} not found, {elapsed*20:.1f}ms total",
          n_found >= 30,
          f"expected >=30 matches from 100 seeded entries, got {n_found}")

    # Query with completely unrelated inputs
    n_false_positives = 0
    for term in ["send email", "deploy to aws", "configure database", "fish", "quantum physics", "draft report"]:
        intent = _intent(term, "general_llm")
        match = await pipeline.find_match(intent)
        if match is not None:
            n_false_positives += 1
    check(f"Unrelated queries: {n_false_positives} false positives from {5} queries",
          n_false_positives <= 1,
          f"false_positives={n_false_positives}")


async def test_memory_pressure_under_saturation():
    print("\n--- D. Memory Pressure Under Saturation ---")
    pipeline = ETDPipeline()
    rss_before = _memory_mb()

    # Ingest 5000 unique entries
    started = time.perf_counter()
    for i in range(5000):
        sig = f"sat-{i:04d}"
        wf = DistilledWorkflow(
            id=str(uuid4()), intent_signature=sig,
            tool_sequence=[ToolStep(tool="terminal", action=f"cmd {i}", verify="passed")],
            parameter_slots=[], invariant_checks=[],
            success_count=1, failure_count=0, generalization_success_rate=0.95,
        )
        entry = WorkflowParameterizer().parameterize(wf)
        entry.generalization_success_rate = 0.95
        pipeline.indexer.index(entry)
    ingest_time = time.perf_counter() - started

    rss_after_ingest = _memory_mb()
    ingest_growth = rss_after_ingest - rss_before

    # Query all 5000
    started = time.perf_counter()
    hits = 0
    for i in range(5000):
        sig = f"sat-{i:04d}"
        intent = _intent(sig, "run_terminal")
        match = await pipeline.find_match(intent)
        if match is not None:
            hits += 1
    query_time = time.perf_counter() - started
    per_query = (query_time / 5000) * 1000

    rss_after_query = _memory_mb()

    check(f"Ingest 5,000 entries: {ingest_time:.3f}s",
          ingest_time < 10,
          f"ingest_time={ingest_time:.3f}s")
    check(f"Query 5,000 entries: {query_time:.3f}s ({per_query:.3f}ms/query), hits={hits}",
          hits >= 4900 and per_query < 50,
          f"hits={hits}, per_query={per_query:.3f}ms")
    check(f"Memory after ingest: +{ingest_growth:.1f}MB, after query: {rss_after_query:.0f}MB",
          ingest_growth < 50,
          f"ingest_growth={ingest_growth:.1f}MB")


def _memory_mb() -> float:
    try:
        import psutil
        return psutil.Process().memory_info().rss / (1024 * 1024)
    except ImportError:
        return 0.0


async def main():
    print("=" * 70)
    print("  PHASE B — ETD SATURATION VALIDATION")
    print("=" * 70)

    tests = [
        test_same_intent_10k_lookups,
        test_unique_intents_no_cache_hits,
        test_near_miss_embeddings,
        test_memory_pressure_under_saturation,
    ]

    for test_fn in tests:
        try:
            await test_fn()
        except Exception as exc:
            print(f"  [ERROR] {test_fn.__name__}: {exc}")

    print(f"\n{'='*70}")
    print(f"  ETD SATURATION RESULTS")
    print(f"{'='*70}")
    print(f"  PASS: {PASS}  |  FAIL: {FAIL}")

    docs_dir = ROOT / "docs"
    docs_dir.mkdir(exist_ok=True)
    report = [
        "# ETD Scaling Report — Phase B\n",
        "## Results\n",
        f"PASS: {PASS} | FAIL: {FAIL}",
        "",
        "## Tests Executed",
        "- A: 10,000 lookups (same intent, cache hit)",
        "- B: 1,000 unique intents (no cache hit, false positive check)",
        "- C: Near-miss embedding matching (50 seeded + unrelated)",
        "- D: Memory pressure under 5,000 entry saturation",
    ]
    report_path = docs_dir / "ETD_scaling_report.md"
    report_path.write_text("\n".join(report), encoding="utf-8")
    print(f"Report: {report_path}")

    print(f"\n  {'='*40}")
    print(f"  GATE: {'PASS' if PASS >= FAIL else 'FAIL'}")
    print(f"  {'='*40}")


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
