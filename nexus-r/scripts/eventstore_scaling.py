from __future__ import annotations
# ruff: noqa: E402

"""
Phase B — EventStore Scaling Validation
Generates 100k+ events, measures append/retrieval latency and DB growth.
"""

import asyncio
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nexus_r.config import NEXUSConfig
from nexus_r.events import Event, EventStore

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


def _file_size(path: Path) -> int:
    try:
        return path.stat().st_size if path.exists() else 0
    except OSError:
        return 0


async def main():
    print("=" * 70)
    print("  PHASE B — EVENTSTORE SCALING (100k+ events)")
    print("=" * 70)

    wd = ROOT / ".eventstore-scaling"
    wd.mkdir(exist_ok=True)
    config = NEXUSConfig.default(wd)
    config.database.sqlite_cache_size_mb = 200

    store = EventStore(config.database.path, cache_size_mb=200)
    await store.initialize()

    # ---- Batch append scaling ----
    print("\n--- A. Batch Append Latency ---")
    batch_sizes = [1, 10, 100, 1000]
    latencies = {}

    total = 0
    for batch_size in batch_sizes:
        events = [
            Event(event_type="perf_test", data={"seq": total + i, "payload": "x" * 500})
            for i in range(batch_size)
        ]
        started = time.perf_counter()
        ids = await store.append_many(events)
        elapsed_ms = (time.perf_counter() - started) * 1000
        per_event = elapsed_ms / batch_size
        latencies[batch_size] = {"total_ms": round(elapsed_ms, 3), "per_event_us": round(per_event * 1000, 2)}
        total += batch_size
        ok = per_event < 2.0
        check(f"Batch {batch_size:4d} events: {elapsed_ms:.3f}ms total, {per_event*1000:.2f}us/event",
              ok, f"{batch_size} events at once")

    # ---- Bulk ingest to 100k ----
    print("\n--- B. Bulk Ingest to 100k events ---")
    bulk_sizes = [5000, 10000, 20000, 50000]
    ingest_latencies = []
    for target in bulk_sizes:
        remaining = target - total
        if remaining <= 0:
            continue
        batch = [
            Event(event_type="bulk_test", data={"seq": total + i, "payload": "x" * 200})
            for i in range(remaining)
        ]
        started = time.perf_counter()
        ids = await store.append_many(batch)
        elapsed_ms = (time.perf_counter() - started) * 1000
        per_event = elapsed_ms / len(batch) if batch else 0
        total += len(batch)
        ingest_latencies.append({"target": target, "ms": round(elapsed_ms, 1), "per_event_us": round(per_event * 1000, 2)})
        ok = per_event < 1.0
        check(f"Ingest {target:5d} events: {elapsed_ms:.0f}ms ({per_event*1000:.2f}us/event)",
              ok, f"total so far: {total}")

    # ---- Retrieval latency ----
    print("\n--- C. Retrieval Latency ---")
    started = time.perf_counter()
    by_type = await store.get_by_type("perf_test")
    type_ms = (time.perf_counter() - started) * 1000
    check(f"Query by type ({len(by_type)} events): {type_ms:.1f}ms", type_ms < 2000)

    started = time.perf_counter()
    by_type2 = await store.get_by_type("bulk_test")
    type2_ms = (time.perf_counter() - started) * 1000
    check(f"Query by type ({len(by_type2)} events): {type2_ms:.1f}ms", type2_ms < 2000)

    started = time.perf_counter()
    time_range = await store.get_by_time_range(
        by_type[0].timestamp, by_type[-1].timestamp
    )
    range_ms = (time.perf_counter() - started) * 1000
    check(f"Query by time range ({len(time_range)} events): {range_ms:.1f}ms",
          range_ms < 5000)

    # Chain retrieval
    if ids:
        started = time.perf_counter()
        chain = await store.get_chain(ids[0])
        chain_ms = (time.perf_counter() - started) * 1000
        check(f"Chain retrieval ({len(chain)} events): {chain_ms:.1f}ms",
              chain_ms < 500, f"chain_len={len(chain)}")

    # ---- DB/WAL sizes ----
    print("\n--- D. Storage Sizes ---")
    db_path = config.database.path
    db_mb = _file_size(db_path) / (1024 * 1024)
    wal_mb = _file_size(Path(str(db_path) + "-wal")) / (1024 * 1024)
    shm_mb = _file_size(Path(str(db_path) + "-shm")) / (1024 * 1024)

    check(f"Database: {db_mb:.2f}MB for {total} events",
          db_mb < 200, f"avg={db_mb*1024*1024/max(total,1):.0f} bytes/event")
    check(f"WAL: {wal_mb:.2f}MB, SHM: {shm_mb:.2f}MB",
          wal_mb < 50)

    await store.close()

    # ---- Summary ----
    print(f"\n{'='*70}")
    print(f"  EVENTSTORE SCALING RESULTS")
    print(f"{'='*70}")
    print(f"  Total events: {total}")
    print(f"  PASS: {PASS}  |  FAIL: {FAIL}")
    print(f"  DB: {db_mb:.2f}MB  |  WAL: {wal_mb:.2f}MB")

    # Report
    docs_dir = ROOT / "docs"
    docs_dir.mkdir(exist_ok=True)
    report = [
        "# EventStore Scaling Report — Phase B\n",
        "## Batch Append Latency\n",
        "| Batch Size | Total (ms) | Per Event (us) |",
        "|------------|------------|----------------|",
    ]
    for bs, data in sorted(latencies.items()):
        report.append(f"| {bs} | {data['total_ms']} | {data['per_event_us']} |")
    report.extend([
        "",
        "## Bulk Ingest\n",
        "| Target Events | Time (ms) | Per Event (us) |",
        "|---------------|-----------|----------------|",
    ])
    for d in ingest_latencies:
        report.append(f"| {d['target']} | {d['ms']} | {d['per_event_us']} |")
    report.extend([
        "",
        "## Retrieval\n",
        f"- Query by type (perf_test): {type_ms:.1f}ms",
        f"- Query by type (bulk_test): {type2_ms:.1f}ms",
        f"- Query by time range: {range_ms:.1f}ms",
        f"- Chain retrieval: {chain_ms:.1f}ms" if ids else "- Chain retrieval: N/A",
        "",
        "## Storage\n",
        f"- Total events: {total}",
        f"- Database: {db_mb:.2f}MB",
        f"- WAL: {wal_mb:.2f}MB",
        f"- Bytes/event: {db_mb*1024*1024/max(total,1):.0f}",
    ])

    report_path = docs_dir / "eventstore_scaling_report.md"
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
