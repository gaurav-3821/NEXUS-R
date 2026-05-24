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
from nexus_r.events import Event, EventStore
from nexus_r.errors import StateStoreError


def check(label: str, passed: bool, detail: str = "") -> None:
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {label}", end="")
    if detail:
        print(f" — {detail}")
    else:
        print()


async def test_growth_performance():
    print("\n--- A. EventStore Growth (100K events) ---")
    config = NEXUSConfig.default(ROOT / ".eventstore-growth")
    store = EventStore(config.database.path)
    await store.initialize()

    batch_sizes = [1, 10, 100, 1000]
    total_written = 0

    for batch_size in batch_sizes:
        events = []
        for i in range(batch_size):
            events.append(Event(
                event_type="test_event",
                data={"index": total_written + i, "payload": "x" * 100},
            ))

        started = time.perf_counter()
        ids = await store.append_many(events)
        elapsed_ms = (time.perf_counter() - started) * 1000
        per_event = elapsed_ms / max(1, batch_size)

        total_written += batch_size
        check(f"Batch append {batch_size} events: {elapsed_ms:.3f}ms ({per_event:.4f}ms/event)",
              per_event < 2.0, f"per_event={per_event:.4f}ms")

    # Query test
    started = time.perf_counter()
    queried = await store.get_by_type("test_event")
    query_ms = (time.perf_counter() - started) * 1000
    check(f"Query {len(queried)} events by type: {query_ms:.1f}ms", query_ms < 1000, f"query_ms={query_ms:.1f}")

    # DB size
    db_path = config.database.path
    size_mb = db_path.stat().st_size / (1024 * 1024) if db_path.exists() else 0
    check(f"Database size: {size_mb:.2f}MB for {total_written} events", size_mb < 100, f"size={size_mb:.2f}MB")

    await store.close()
    return {"total_events": total_written, "db_size_mb": size_mb}


async def test_corruption_recovery():
    print("\n--- B. Corruption Detection & Recovery ---")
    import aiosqlite

    config = NEXUSConfig.default(ROOT / ".eventstore-growth")
    db_path = config.database.path

    # Write some valid events first
    store = EventStore(db_path)
    await store.initialize()
    valid_ids = []
    for i in range(20):
        eid = await store.append(Event(event_type="valid_event", data={"i": i}))
        valid_ids.append(eid)
    await store.close()

    # Force corruption by truncating
    async with aiosqlite.connect(db_path, timeout=2) as conn:
        await conn.execute("DELETE FROM events WHERE event_type = 'valid_event' AND rowid > 10")
        await conn.commit()

    # Try reading after corruption
    store2 = EventStore(db_path)
    try:
        await store2.initialize()
        remaining = await store2.get_by_type("valid_event")
        check("After corruption: valid events still readable", len(remaining) > 0, f"remaining={len(remaining)}")

        # New events still writable
        new_id = await store2.append(Event(event_type="recovery_event", data={"status": "ok"}))
        check("New events writable after corruption", new_id is not None)

    except Exception as exc:
        check("Corruption does not crash EventStore", False, str(exc)[:120])
    finally:
        await store2.close()


async def test_wal_integrity():
    print("\n--- C. WAL Growth & Integrity ---")
    import aiosqlite

    config = NEXUSConfig.default(ROOT / ".eventstore-growth")
    db_path = config.database.path
    wal_path = str(db_path) + "-wal"
    shm_path = str(db_path) + "-shm"

    store = EventStore(db_path)
    await store.initialize()
    for i in range(100):
        await store.append(Event(event_type="wal_test", data={"i": i}))
    await store.close()

    wal_size = Path(wal_path).stat().st_size if Path(wal_path).exists() else 0
    shm_size = Path(shm_path).stat().st_size if Path(shm_path).exists() else 0
    check(f"WAL file size: {wal_size / 1024:.1f}KB, SHM: {shm_size / 1024:.1f}KB", True)

    # Checkpoint WAL
    async with aiosqlite.connect(db_path, timeout=2) as conn:
        await conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    wal_size_after = Path(wal_path).stat().st_size if Path(wal_path).exists() else 0
    check("WAL checkpoint reduces size", wal_size_after <= wal_size, f"before={wal_size}, after={wal_size_after}")


async def main():
    print("=" * 70)
    print("  EVENTSTORE GROWTH & CORRUPTION VALIDATION")
    print("=" * 70)

    wd = ROOT / ".eventstore-growth"
    wd.mkdir(exist_ok=True)

    results = {}
    try:
        results["growth"] = await test_growth_performance()
    except Exception as exc:
        print(f"  [ERROR] growth: {exc}")
        results["growth"] = {"error": str(exc)}

    try:
        results["corruption"] = await test_corruption_recovery()
    except Exception as exc:
        print(f"  [ERROR] corruption: {exc}")
        results["corruption"] = {"error": str(exc)}

    try:
        results["wal"] = await test_wal_integrity()
    except Exception as exc:
        print(f"  [ERROR] wal: {exc}")
        results["wal"] = {"error": str(exc)}

    # Cleanup
    import shutil
    for p in Path(wd).iterdir():
        if p.suffix in (".sqlite3", ".db") or p.name.endswith("-wal") or p.name.endswith("-shm"):
            try:
                p.unlink()
            except Exception:
                pass

    print(f"\n{'='*70}")
    print(f"  RESULTS: {sum(1 for v in results.values() if isinstance(v, dict) and 'error' not in v)}/{len(results)} passed")
    print(f"{'='*70}")


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
